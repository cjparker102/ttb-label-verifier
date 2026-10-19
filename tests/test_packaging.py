"""Guards on what goes into the container image."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def dockerignore_entries():
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def test_secrets_and_private_files_stay_out_of_the_image():
    assert {".env", ".env.*", "private/", ".claude/", ".git/"} <= dockerignore_entries()


def test_image_copies_only_what_the_app_needs():
    copies = [
        line.split()[1:]
        for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
        if line.startswith("COPY") and "--from=" not in line
    ]
    assert copies == [["pyproject.toml", "uv.lock", "./"], ["app", "./app"]]


def test_app_runs_as_a_non_root_user():
    lines = (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    users = [line.split()[1] for line in lines if line.startswith("USER ")]
    assert users and users[-1] not in ("root", "0")


def test_image_includes_tesseract_for_basic_text_reading():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "tesseract-ocr tesseract-ocr-eng" in dockerfile


def test_ci_installs_tesseract_so_its_tests_run():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "tesseract-ocr" in workflow
