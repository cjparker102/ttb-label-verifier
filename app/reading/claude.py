"""Reads a label with Claude through the Anthropic API."""

import base64
import time
from dataclasses import dataclass

import anthropic

from app.reading.prompt import INSTRUCTIONS
from app.reading.schema import LabelReading

MODEL = "claude-haiku-5-5"


class ReadingFailed(Exception):
    """Claude did not return a usable reading."""


@dataclass
class ReadResult:
    reading: LabelReading
    seconds: float
    input_tokens: int
    output_tokens: int
    requests: int = 1  # 2 when a slow answer was asked for again (HedgedReader)


class ClaudeReader:
    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        *,
        thinking: bool,
        effort: str = "low",
        model: str = MODEL,
        max_tokens: int = 8000,
    ):
        self.client = client
        self.thinking = thinking
        self.effort = effort
        self.model = model
        self.max_tokens = max_tokens

    async def read(self, images: list[bytes]) -> ReadResult:
        """Read one product's label images, each already a JPEG."""
        content: list[dict] = []
        for number, image in enumerate(images, start=1):
            content.append({"type": "text", "text": f"Image {number}:"})
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64.standard_b64encode(image).decode("ascii"),
                    },
                }
            )
        content.append({"type": "text", "text": "Read this label."})

        start = time.perf_counter()
        response = await self.client.messages.parse(
            model=self.model,
            max_tokens=self.max_tokens,
            system=INSTRUCTIONS,
            thinking={"type": "adaptive"} if self.thinking else {"type": "disabled"},
            output_config={"effort": self.effort},
            messages=[{"role": "user", "content": content}],
            output_format=LabelReading,
        )
        seconds = time.perf_counter() - start

        if response.stop_reason != "end_turn" or response.parsed_output is None:
            raise ReadingFailed(f"Claude stopped with reason: {response.stop_reason}")
        return ReadResult(
            reading=response.parsed_output,
            seconds=seconds,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
