"""Builds the AI reader the settings ask for: Claude through the Anthropic API, or
Claude in Microsoft Foundry (Azure). Basic text reading needs no reader object."""

import asyncio
import os
import time
from collections import deque

import anthropic

from app.config import Settings
from app.reading.claude import ClaudeReader, ReadResult

FOUNDRY_SCOPE = "https://ai.azure.com/.default"


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


def foundry_client(settings: Settings, http_client=None, credential_factory=None):
    options = {"resource": settings.foundry_resource, "max_retries": 1, "timeout": 30}
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


def make_reader(settings: Settings, http_client=None, credential_factory=None):
    """The AI reader for these settings, or None when there is none: basic text reading
    only, or no Anthropic credentials on this server."""
    if settings.reader == "ocr":
        return None
    if settings.reader == "foundry":
        client = foundry_client(settings, http_client, credential_factory)
    else:
        options = {"max_retries": 1, "timeout": 30}
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
