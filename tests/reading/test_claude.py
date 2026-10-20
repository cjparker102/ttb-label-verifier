"""Tests for the Claude reader's request and error handling.

The network call is replaced by a stand-in that records the request and returns
a fixed response, so these tests run offline and cost nothing.
"""

import asyncio
import base64
from types import SimpleNamespace

import pytest

from app.reading.claude import MODEL, ClaudeReader, ReadingFailed
from app.reading.prompt import INSTRUCTIONS
from app.reading.schema import LabelReading
from tests.stand_ins import recorded_reading

PARSED = object()  # the reader passes the parsed reading through untouched


class StandInMessages:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def parse(self, **request):
        self.requests.append(request)
        return self.response


def stand_in_client(stop_reason="end_turn", parsed=PARSED):
    response = SimpleNamespace(
        stop_reason=stop_reason,
        parsed_output=parsed,
        usage=SimpleNamespace(input_tokens=1200, output_tokens=300),
    )
    return SimpleNamespace(messages=StandInMessages(response))


def read(reader, images):
    return asyncio.run(reader.read(images))


def test_images_are_sent_numbered_and_in_order():
    client = stand_in_client()
    read(ClaudeReader(client, thinking=False), [b"front", b"back"])
    content = client.messages.requests[0]["messages"][0]["content"]
    assert [block["type"] for block in content] == ["text", "image", "text", "image", "text"]
    assert content[0]["text"] == "Image 1:"
    assert content[2]["text"] == "Image 2:"
    assert base64.b64decode(content[1]["source"]["data"]) == b"front"
    assert base64.b64decode(content[3]["source"]["data"]) == b"back"
    assert content[1]["source"]["media_type"] == "image/jpeg"


def test_request_settings():
    client = stand_in_client()
    read(ClaudeReader(client, thinking=False, effort="low"), [b"label"])
    request = client.messages.requests[0]
    assert request["model"] == MODEL
    assert request["system"] == INSTRUCTIONS
    assert request["output_format"] is LabelReading
    assert request["output_config"] == {"effort": "low"}
    assert request["thinking"] == {"type": "disabled"}


def test_thinking_setting_turns_on_adaptive_thinking():
    client = stand_in_client()
    read(ClaudeReader(client, thinking=True), [b"label"])
    assert client.messages.requests[0]["thinking"] == {"type": "adaptive"}


def test_returns_reading_and_token_counts():
    result = read(ClaudeReader(stand_in_client(), thinking=False), [b"label"])
    assert result.reading is PARSED
    assert (result.input_tokens, result.output_tokens) == (1200, 300)
    assert result.seconds >= 0


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_incomplete_response_raises(stop_reason):
    with pytest.raises(ReadingFailed):
        read(ClaudeReader(stand_in_client(stop_reason=stop_reason), thinking=False), [b"label"])


def test_missing_parsed_output_raises():
    with pytest.raises(ReadingFailed):
        read(ClaudeReader(stand_in_client(parsed=None), thinking=False), [b"label"])


def test_the_reader_is_told_to_copy_the_warning_as_printed():
    # An approved label misspells a word in the warning, and Claude read it spelt correctly.
    assert "Copy it letter by letter as printed" in INSTRUCTIONS
    assert "Never write it from memory" in INSTRUCTIONS


def test_the_reader_reports_every_alcohol_and_net_contents_statement():
    required = LabelReading.model_json_schema()["required"]
    assert "alcohol_statements" in required and "net_contents_statements" in required
    assert "report each one" in INSTRUCTIONS
    # Readings saved before the lists existed still load, with empty lists.
    old = recorded_reading()
    assert (old.alcohol_statements, old.net_contents_statements) == ([], [])


def test_the_reader_is_told_to_copy_the_whole_alcohol_statement():
    # A real photo of a bottle printed "ALC. 5% BY VOL", and Claude read "5% BY VOL", which
    # the alcohol form check then flagged (Oct 20, 2026).
    assert 'such as "ALC.", "ALCOHOL", "BY VOL", or "ABV"' in INSTRUCTIONS
    assert "Never shorten it to the number" in INSTRUCTIONS
    assert "each copied whole and exactly as printed" in INSTRUCTIONS


def test_the_reader_is_told_capitals_alone_are_not_bold():
    # A sample whose heading is in capitals but not bold was read as bold 6 times in 6 with
    # an earlier prompt, and 1 time in 8 with this one (Oct 20, 2026).
    assert "visibly thicker and darker" in INSTRUCTIONS
    assert "Capital letters, a colon, or a larger size alone do not make the" in INSTRUCTIONS
