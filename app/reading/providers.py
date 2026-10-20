"""Builds the AI reader the settings ask for: Claude through the Anthropic API, or
Claude in Microsoft Foundry (Azure). Basic text reading needs no reader object."""

import asyncio
import dataclasses
import logging
import os
import time
from collections import deque

import anthropic

from app.config import Settings
from app.reading.claude import ClaudeReader, ReadingFailed, ReadResult

FOUNDRY_SCOPE = "https://ai.azure.com/.default"

log = logging.getLogger("ttb_label_verifier")


def has_credentials(client) -> bool:
    """The SDK builds a client without credentials and only complains when it sends a
    request, so check what it found: an API key, a token, or federated credentials."""
    return any(
        getattr(client, name, None) is not None for name in ("api_key", "auth_token", "credentials")
    )


def entra_token_provider(credential_factory=None):
    """An async token provider for Foundry that signs in with Microsoft Entra ID. In Azure
    that is the container app's managed identity, so no key is stored anywhere."""
    if credential_factory is None:
        from azure.identity import DefaultAzureCredential

        credential_factory = DefaultAzureCredential
    from azure.identity import get_bearer_token_provider

    get_token = get_bearer_token_provider(credential_factory(), FOUNDRY_SCOPE)

    async def token() -> str:
        # The Azure library is synchronous; fetch (or reuse) the token off the event loop.
        return await asyncio.to_thread(get_token)

    return token


def client_options(settings: Settings) -> dict:
    """A connection must open within settings.connect_seconds and a request answer within
    the reading deadline. One retry, for a passing error; the deadline still holds."""
    return {
        "max_retries": 1,
        "timeout": anthropic.Timeout(
            settings.reading_deadline_seconds, connect=settings.connect_seconds
        ),
    }


def foundry_client(settings: Settings, http_client=None, credential_factory=None):
    options = {"resource": settings.foundry_resource, **client_options(settings)}
    if http_client is not None:
        options["http_client"] = http_client
    api_key = os.environ.get("ANTHROPIC_FOUNDRY_API_KEY")
    if api_key:  # for trying Foundry from a laptop; in Azure the managed identity is used
        return anthropic.AsyncAnthropicFoundry(api_key=api_key, **options)
    return anthropic.AsyncAnthropicFoundry(
        azure_ad_token_provider=entra_token_provider(credential_factory), **options
    )


class PacedReader:
    """Sends at most `per_minute` labels a minute to the wrapped reader, waiting when
    needed. Claude in Foundry starts with a small quota; pacing makes a batch slow down
    instead of failing."""

    def __init__(self, reader, per_minute: int, clock=time.monotonic, sleep=asyncio.sleep):
        self.reader = reader
        self.per_minute = per_minute
        self.clock = clock
        self.sleep = sleep
        self.starts: deque[float] = deque()
        self.lock = asyncio.Lock()

    async def read(self, images: list[bytes]) -> ReadResult:
        async with self.lock:
            while True:
                now = self.clock()
                while self.starts and now - self.starts[0] >= 60:
                    self.starts.popleft()
                if len(self.starts) < self.per_minute:
                    break
                await self.sleep(60 - (now - self.starts[0]))
            self.starts.append(now)
        return await self.reader.read(images)


class DeadlineReader:
    """Gives up on the wrapped reader after `seconds`, so a check falls back to basic text
    reading instead of waiting on a provider that can't be reached."""

    def __init__(self, reader, seconds: float):
        self.reader = reader
        self.seconds = seconds

    async def read(self, images: list[bytes]) -> ReadResult:
        try:
            return await asyncio.wait_for(self.reader.read(images), self.seconds)
        except TimeoutError as error:
            raise ReadingFailed(f"No answer within {self.seconds:g} s") from error


class HedgedReader:
    """Asks the wrapped reader again when its answer is slow, and uses whichever answer
    comes first. Claude usually reads a label in 2 to 3 seconds, but now and then takes
    8 or more; a second request may then answer sooner. The other request is cancelled.
    Both are paid for, so the result counts the tokens twice."""

    def __init__(self, reader, after: float):
        self.reader = reader
        self.after = after  # seconds

    async def read(self, images: list[bytes]) -> ReadResult:
        start = time.perf_counter()
        tasks = [asyncio.create_task(self.reader.read(images))]
        try:
            done, _ = await asyncio.wait(tasks, timeout=self.after)
            if not done:
                tasks.append(asyncio.create_task(self.reader.read(images)))
            waiting, failures = set(tasks), []
            while waiting:
                done, waiting = await asyncio.wait(waiting, return_when=asyncio.FIRST_COMPLETED)
                for task in sorted(done, key=tasks.index):
                    if task.exception() is not None:
                        failures.append(task.exception())
                        continue
                    result = task.result()
                    if len(tasks) == 1:
                        return result
                    seconds = time.perf_counter() - start
                    log.warning(
                        "No answer after %g s, so the label was read again. "
                        "The %s request answered first, after %.1f s.",
                        self.after,
                        "first" if task is tasks[0] else "second",
                        seconds,
                    )
                    # The other request, cancelled or failed, is counted as costing the same.
                    return dataclasses.replace(
                        result,
                        seconds=seconds,
                        input_tokens=result.input_tokens * 2,
                        output_tokens=result.output_tokens * 2,
                        requests=2,
                    )
            raise failures[0]
        finally:
            for task in tasks:
                task.cancel()  # does nothing to a request that has finished


def make_reader(settings: Settings, http_client=None, credential_factory=None):
    """The AI reader for these settings, or None when there is none: basic text reading
    only, or no Anthropic credentials on this server."""
    if settings.reader == "ocr":
        return None
    if settings.reader == "foundry":
        client = foundry_client(settings, http_client, credential_factory)
    else:
        options = client_options(settings)
        if http_client is not None:
            options["http_client"] = http_client
        try:
            client = anthropic.AsyncAnthropic(**options)
        except anthropic.AnthropicError:
            return None
        if not has_credentials(client):
            return None
    reader = ClaudeReader(
        client, thinking=settings.thinking, effort=settings.effort, model=settings.model
    )
    if settings.labels_per_minute:
        return PacedReader(reader, settings.labels_per_minute)
    return reader
