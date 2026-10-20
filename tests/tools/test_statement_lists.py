"""tools/statement_lists.py: the reader with and without its statement lists."""

from app.reading.prompt import INSTRUCTIONS
from app.reading.schema import LabelReading
from tools.statement_lists import LIST_FIELDS, WITH, WITHOUT, report, without_lists


def test_only_the_lists_are_taken_out():
    prompt, schema = without_lists()
    assert "alcohol_statements" not in prompt and "net_contents_statements" not in prompt
    assert INSTRUCTIONS.startswith(prompt.rstrip("\n"))
    assert "image_problems: anything that makes an image hard to read." in prompt
    kept = set(LabelReading.model_fields) - LIST_FIELDS
    assert set(schema.model_fields) == kept
    assert (
        schema.model_json_schema()["properties"]["government_warning"]
        == (LabelReading.model_json_schema()["properties"]["government_warning"])
    )


def row(label, variant, seconds, tokens, name="samples"):
    return {"set": name, "round": 0, "id": label, "variant": variant, "seconds": seconds,
            "output_tokens": tokens, "input_tokens": 1000}  # fmt: skip


def test_the_report_pairs_each_label_and_gives_totals_only():
    rows = [
        row("a", WITH, 3.0, 500), row("a", WITHOUT, 2.5, 460),
        row("b", WITH, 2.0, 480), row("b", WITHOUT, 2.2, 440),
        row("26000000000001", WITH, 5.0, 600, "cola-fourth"),
        row("26000000000001", WITHOUT, 3.0, 560, "cola-fourth"),
    ]  # fmt: skip
    text = report(rows)
    assert "| with lists | 2 | 490 | 2.50 s / 3.00 s / 3.00 s | 0 |" in text
    assert "| Difference, label by label (2 pairs) | | +40 |" in text
    assert "slower with lists in 1 of 2" in text
    assert "| with lists | 1 | 600 | 5.00 s / 5.00 s / 5.00 s | 1 |" in text
    assert "26000000000001" not in text  # no label of a private set is named
