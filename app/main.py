"""Web entry point for the TTB Label Verifier."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# The interactive API docs load scripts from an outside CDN, so they stay off.
app = FastAPI(title="TTB Label Verifier", docs_url=None, redoc_url=None, openapi_url=None)

HOME_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TTB Label Verifier</title>
</head>
<body>
  <main>
    <h1>TTB Label Verifier</h1>
    <p>This app is being built. Label checking is coming soon.</p>
  </main>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HOME_PAGE


@app.get("/health")
def health() -> dict[str, str]:
    """Lets Azure confirm the app is running."""
    return {"status": "ok"}
