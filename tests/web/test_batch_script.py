"""The batch page's script, run in Node with a stand-in page, network, and timers, so its
reconnecting and expired-batch handling is tested as written. Skipped without Node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "app" / "static" / "app.js"
NODE = shutil.which("node")

HARNESS = r"""
import vm from "node:vm";
import fs from "node:fs";

const [scriptPath, scenarioJson] = process.argv.slice(2);
const scenario = JSON.parse(scenarioJson);
const elements = {};
const element = (id, extra = {}) => {
  const history = [];
  let text = "";
  elements[id] = {
    id, hidden: true, innerHTML: "", dataset: {}, history, ...extra,
    get textContent() { return text; },
    set textContent(value) { text = value; history.push(value); },
  };
};
element("batch", { dataset: { job: "abc", state: "running" } });
element("batch-announce");
element("batch-connection");
element("batch-results");

const timers = [];
const delays = [];
let fetches = 0;
const respond = ({ error, status = 200, json = {}, text = "" }) => {
  if (error) return Promise.reject(new TypeError("Failed to fetch"));
  return Promise.resolve({
    status, ok: status >= 200 && status < 300,
    json: () => Promise.resolve(json), text: () => Promise.resolve(text),
  });
};
const progress = [...scenario.progress];
const context = vm.createContext({
  document: {
    addEventListener: () => {},
    getElementById: (id) => elements[id] || null,
    querySelectorAll: () => [],
    querySelector: () => null,
  },
  fetch: (url) => {
    fetches += 1;
    if (url.endsWith("/results")) return respond(scenario.results || { text: "<p>results</p>" });
    const done = { json: { state: "finished", done: 1, total: 1 } };
    return respond(progress.length ? progress.shift() : done);
  },
  setTimeout: (fn, ms) => timers.push([fn, ms]),
  Math, Error, TypeError, JSON, Promise, console,
});
vm.runInContext(fs.readFileSync(scriptPath, "utf8"), context);
context.watchBatch();
for (let step = 0; timers.length && step < 40; step += 1) {
  const [fn, ms] = timers.shift();
  delays.push(ms);
  await fn();
}
const connection = elements["batch-connection"];
console.log(JSON.stringify({
  delays, fetches, pending: timers.length,
  shown: connection.history, hidden: connection.hidden,
  announce: elements["batch-announce"].textContent,
  results: elements["batch-results"].innerHTML,
}));
"""


def run(tmp_path, scenario):
    harness = tmp_path / "harness.mjs"
    harness.write_text(HARNESS, encoding="utf-8")
    finished = subprocess.run(
        [NODE, str(harness), str(SCRIPT), json.dumps(scenario)],
        capture_output=True, text=True, timeout=30, check=True,
    )  # fmt: skip
    return json.loads(finished.stdout)


pytestmark = pytest.mark.skipif(NODE is None, reason="Node is not installed")

RUNNING = {"json": {"state": "running", "done": 1, "total": 3}}
FINISHED = {"json": {"state": "finished", "done": 3, "total": 3}}


def test_lost_contact_shows_reconnecting_then_clears(tmp_path):
    out = run(tmp_path, {"progress": [RUNNING, {"error": True}, {"status": 502}, FINISHED]})
    assert out["shown"][:2] == ["Lost contact with the app. Reconnecting…"] * 2
    assert out["shown"][-1] == "" and out["hidden"] is True  # cleared once back
    assert out["delays"] == [1000, 2000, 2000, 4000]  # waits longer after each failure
    assert out["announce"] == "The batch is finished."
    assert out["results"] == "<p>results</p>"


def test_a_long_outage_says_the_batch_keeps_running(tmp_path):
    out = run(tmp_path, {"progress": [{"error": True}] * 12 + [FINISHED]})
    assert out["shown"][9].startswith("Still reconnecting. The batch keeps running")
    assert max(out["delays"]) == 15000  # never waits more than 15 seconds
    assert out["announce"] == "The batch is finished."


def test_an_expired_batch_says_so_and_stops(tmp_path):
    message = "These batch results are no longer available."
    gone = {"status": 404, "json": {"state": "gone", "message": message}}
    out = run(tmp_path, {"progress": [RUNNING, gone]})
    assert out["shown"] == [message] and out["hidden"] is False
    assert out["announce"] == message
    assert out["pending"] == 0  # no more polling


def test_results_that_fail_to_load_are_retried(tmp_path):
    out = run(tmp_path, {"progress": [RUNNING, RUNNING], "results": {"status": 500}})
    assert "Lost contact with the app. Reconnecting…" in out["shown"]
