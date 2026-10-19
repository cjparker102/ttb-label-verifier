import csv
import json

from app.rules.warning import GOVERNMENT_WARNING
from tools.make_samples import (
    LABELS_DIR,
    SAMPLES,
    SAMPLES_DIR,
    application_rows,
    expected_entries,
)


def load_expected():
    with open(SAMPLES_DIR / "expected.json", encoding="utf-8") as f:
        return json.load(f)


def test_saved_expected_results_match_the_generator():
    # Fails if a sample was changed without rerunning: uv run python -m tools.make_samples
    assert load_expected() == expected_entries()


def test_saved_applications_match_the_generator():
    with open(SAMPLES_DIR / "applications.csv", newline="", encoding="utf-8") as f:
        assert list(csv.DictReader(f)) == application_rows()


def test_every_sample_image_exists():
    for entry in load_expected():
        for name in entry["images"]:
            assert (LABELS_DIR / name).is_file(), name


def test_sample_ids_are_unique():
    ids = [sample.id for sample in SAMPLES]
    assert len(ids) == len(set(ids))


def test_warning_expectations_match_what_is_printed():
    for entry in load_expected():
        warning = entry["truth"]["government_warning"]
        printed_correctly = warning["text"] == GOVERNMENT_WARNING and warning["heading_bold"]
        expected_pass = entry["expected"]["government_warning"] == "pass"
        assert printed_correctly == expected_pass, entry["id"]


def test_only_imports_expect_a_country_of_origin():
    for sample in SAMPLES:
        is_import = bool(sample.application["country_of_origin"])
        expects_country = sample.expected["country_of_origin"] != "not_needed"
        assert is_import == expects_country, sample.id
