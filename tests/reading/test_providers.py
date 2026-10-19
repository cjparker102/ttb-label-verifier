"""The real Anthropic SDK clients, with the network replaced by a recorder.

The SDK builds and sends each request exactly as it would to Anthropic or Azure;
the recorder keeps what was sent and answers with a recorded reading. So these
tests check the actual addresses, sign-in headers, and request bodies, offline.
"""

import asyncio
import json
import time

import httpx2
import pytest
from azure.core.credentials import AccessToken

from app.config import Settings, load_settings
from app.reading.providers import PacedReader, make_reader
from tests.stand_ins import recorded_reading

READING = recorded_reading()


class Recorder:
    def __init__(self):
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        body = json.loads(request.content)
        return httpx2.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": body["model"],
                "content": [{"type": "text", "text": READING.model_dump_json()}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 4739, "output_tokens": 430},
            },
        )

    def client(self) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(transport=httpx2.MockTransport(self))


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """No credentials from the machine running the tests can leak in."""
    for name in (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_PROFILE",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_FOUNDRY_API_KEY",
        "ANTHROPIC_FOUNDRY_RESOURCE",
        "ANTHROPIC_FOUNDRY_BASE_URL",
        "ANTHROPIC_FEDERATION_RULE_ID",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return monkeypatch


def read_once(reader):
    return asyncio.run(reader.read([b"\xff\xd8\xff picture"]))


def test_anthropic_api_request(clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    recorder = Recorder()
    result = read_once(make_reader(Settings(), http_client=recorder.client()))
    request = recorder.requests[0]
    body = json.loads(request.content)
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert request.headers["x-api-key"] == "test-key-not-real"
    assert body["model"] == "claude-haiku-5-5"
    assert body["thinking"] == {"type": "disabled"}
    assert body["output_config"]["effort"] == "low"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert result.reading == READING
    assert (result.input_tokens, result.output_tokens) == (4739, 430)


FOUNDRY = Settings(reader="foundry", foundry_resource="ttb-test", thinking=True)
FOUNDRY_URL = "https://ttb-test.services.ai.azure.com/anthropic/v1/messages"


def test_foundry_request_with_a_key(clean_env):
    clean_env.setenv("ANTHROPIC_FOUNDRY_API_KEY", "foundry-key-not-real")
    recorder = Recorder()
    result = read_once(make_reader(FOUNDRY, http_client=recorder.client()))
    request = recorder.requests[0]
    assert str(request.url) == FOUNDRY_URL
    assert "foundry-key-not-real" in (
        request.headers.get("api-key"),
        request.headers.get("x-api-key"),
    )
    assert json.loads(request.content)["thinking"] == {"type": "adaptive"}
    assert result.reading == READING


def test_foundry_signs_in_with_entra_and_stores_no_key(clean_env):
    class FakeManagedIdentity:
        scopes = []

        def get_token(self, *scopes, **kwargs):
            self.scopes.extend(scopes)
            return AccessToken("entra-token", int(time.time()) + 3600)

    recorder = Recorder()
    reader = make_reader(
        FOUNDRY, http_client=recorder.client(), credential_factory=FakeManagedIdentity
    )
    read_once(reader)
    request = recorder.requests[0]
    assert str(request.url) == FOUNDRY_URL
    assert request.headers["authorization"] == "Bearer entra-token"
    assert FakeManagedIdentity.scopes == ["https://ai.azure.com/.default"]


def test_no_reader_for_basic_text_reading_or_without_credentials(clean_env):
    assert make_reader(Settings(reader="ocr")) is None
    assert make_reader(Settings()) is None  # Anthropic API, but no key on this machine


def test_pacing_waits_once_the_minute_is_full():
    now, waits = [0.0], []

    class Instant:
        async def read(self, images):
            return "read"

    async def fake_sleep(seconds):
        waits.append(seconds)
        now[0] += seconds

    paced = PacedReader(Instant(), per_minute=2, clock=lambda: now[0], sleep=fake_sleep)

    async def three_reads():
        for elapsed in (0, 10, 20):
            now[0] = elapsed
            await paced.read([])

    asyncio.run(three_reads())
    assert waits == [40.0]  # the third read waits until a minute after the first


def test_pacing_is_on_when_set():
    settings = load_settings({"TTB_READER": "ocr", "TTB_LABELS_PER_MINUTE": "8"})
    assert settings.labels_per_minute == 8


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"TTB_READER": "foundry"}, "TTB_FOUNDRY_RESOURCE"),
        (
            {"TTB_READER": "foundry", "TTB_FOUNDRY_RESOURCE": "x", "TTB_CLAUDE_THINKING": "off"},
            "adaptive",
        ),
        ({"TTB_READER": "openai"}, "TTB_READER"),
        ({"TTB_LABELS_PER_MINUTE": "lots"}, "whole number"),
        ({"TTB_BATCH_CONCURRENCY": "0"}, "at least 1"),
    ],
)
def test_bad_provider_settings_stop_the_app_at_startup(env, message):
    with pytest.raises(ValueError, match=message):
        load_settings(env)


def test_foundry_settings_default_to_thinking_on():
    settings = load_settings({"TTB_READER": "foundry", "TTB_FOUNDRY_RESOURCE": "ttb-test"})
    assert (settings.reader, settings.thinking, settings.foundry_resource) == (
        "foundry",
        True,
        "ttb-test",
    )
