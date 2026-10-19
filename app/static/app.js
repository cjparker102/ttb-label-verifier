// Small helpers. The pages work without them.
document.addEventListener("DOMContentLoaded", () => {
  const busyOnSubmit = (formId, buttonId, busyId, busyText) => {
    const form = document.getElementById(formId);
    if (!form) return;
    form.addEventListener("submit", () => {
      const button = document.getElementById(buttonId);
      button.disabled = true;
      button.textContent = busyText;
      document.getElementById(busyId).hidden = false;
    });
  };
  busyOnSubmit("check-form", "check-button", "busy", "Checking…");
  busyOnSubmit("batch-form", "batch-button", "batch-busy", "Uploading…");

  // After a check, move keyboard and screen-reader focus to what changed.
  const target = document.getElementById("errors") || document.getElementById("results-heading");
  if (target) {
    target.focus();
  }

  watchBatch();
});

// While a batch runs, keep its page up to date without reloading it.
function watchBatch() {
  const batch = document.getElementById("batch");
  if (!batch || batch.dataset.state === "finished") return;
  const id = batch.dataset.job;
  const announce = document.getElementById("batch-announce");
  let lastDone = -1;
  let lastState = batch.dataset.state;

  const update = async () => {
    try {
      const response = await fetch(`/batches/${id}/progress`, { cache: "no-store" });
      if (!response.ok) return;
      const progress = await response.json();
      if (progress.done !== lastDone || progress.state !== lastState) {
        lastDone = progress.done;
        lastState = progress.state;
        const open = [...document.querySelectorAll("details[data-key][open]")].map((d) => d.dataset.key);
        const html = await (await fetch(`/batches/${id}/results`, { cache: "no-store" })).text();
        document.getElementById("batch-results").innerHTML = html;
        open.forEach((key) => {
          const details = document.querySelector(`details[data-key="${key}"]`);
          if (details) details.open = true;
        });
        announce.textContent =
          progress.state === "finished"
            ? "The batch is finished."
            : `${progress.done} of ${progress.total} labels checked.`;
      }
      if (progress.state !== "finished") setTimeout(update, 2000);
    } catch {
      setTimeout(update, 5000);
    }
  };
  setTimeout(update, 1000);
}
