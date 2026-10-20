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

  // Sample buttons and other one-button forms say they're working once pressed.
  document.querySelectorAll("form[data-busy]").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("button");
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      const title = button.querySelector(".sample-title") || button;
      title.textContent = form.dataset.busy;
    });
  });

  // After a check, move keyboard and screen-reader focus to what changed.
  const target = document.getElementById("errors") || document.getElementById("results-heading");
  if (target) {
    target.focus();
  }

  setUpDropZones();
  watchBatch();
});

// Drag and drop onto the file boxes. The plain file pickers work without this.
function setUpDropZones() {
  // A file dropped anywhere else would make the browser open it and leave the page.
  ["dragover", "drop"].forEach((type) => window.addEventListener(type, (event) => event.preventDefault()));

  document.querySelectorAll(".drop-zone").forEach((zone) => {
    const input = document.getElementById(zone.dataset.dropFor);
    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      zone.classList.add("dragging");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      zone.classList.remove("dragging");
      placeFiles(zone, [...event.dataTransfer.files]);
    });
    input.addEventListener("change", () => showChosen(input));
    showChosen(input);
    zone.classList.add("counting");
  });
}

// Put dropped files in the right box. In the batch form, a spreadsheet goes to the
// spreadsheet box and everything else to the pictures box, whichever zone it lands on.
function placeFiles(zone, files) {
  const form = zone.closest("form");
  const spreadsheetBox = form.querySelector("#spreadsheet");
  const isSpreadsheet = (file) => /\.(csv|xlsx)$/i.test(file.name);
  const target = (file) => {
    if (!spreadsheetBox) return document.getElementById(zone.dataset.dropFor);
    return isSpreadsheet(file) ? spreadsheetBox : form.querySelector("#pictures");
  };
  const byBox = new Map();
  files.forEach((file) => {
    const box = target(file);
    byBox.set(box, [...(byBox.get(box) || []), file]);
  });
  byBox.forEach((chosen, box) => {
    const transfer = new DataTransfer();
    (box.multiple ? chosen : chosen.slice(-1)).forEach((file) => transfer.items.add(file));
    box.files = transfer.files;
    showChosen(box);
  });
}

function showChosen(input) {
  const list = document.querySelector(`[data-chosen-for="${input.id}"]`);
  const files = [...input.files];
  // Our own words for what is chosen, in place of the browser's "No file chosen".
  const count = document.querySelector(`[data-count-for="${input.id}"]`);
  if (files.length === 0) count.textContent = count.dataset.none;
  else if (files.length === 1) count.textContent = count.dataset.one;
  else count.textContent = count.dataset.many.replace("{n}", files.length);
  count.hidden = false;
  const shown = files.slice(0, 8).map((file) => {
    const item = document.createElement("li");
    const size =
      file.size < 1048576
        ? `${Math.max(1, Math.round(file.size / 1024))} KB`
        : `${(file.size / 1048576).toFixed(1)} MB`;
    item.textContent = `${file.name} (${size})`;
    return item;
  });
  if (files.length > 8) {
    const more = document.createElement("li");
    more.textContent = `and ${files.length - 8} more`;
    shown.push(more);
  }
  list.replaceChildren(...shown);
}

// While a batch runs, keep its page up to date without reloading it. If the app can't be
// reached, say so and keep trying, waiting longer each time; if the batch has expired,
// say so and stop.
function watchBatch() {
  const batch = document.getElementById("batch");
  if (!batch || batch.dataset.state === "finished") return;
  const id = batch.dataset.job;
  const announce = document.getElementById("batch-announce");
  const connection = document.getElementById("batch-connection");
  let lastDone = -1;
  let lastState = batch.dataset.state;
  let failures = 0;

  const show = (text) => {
    connection.textContent = text;
    connection.hidden = !text;
  };
  const gone = async (response) => {
    const answer = await response.json().catch(() => ({}));
    const text = answer.message || "These batch results are no longer available.";
    show(text);
    announce.textContent = text;
  };

  const update = async () => {
    try {
      const response = await fetch(`/batches/${id}/progress`, { cache: "no-store" });
      if (response.status === 404) return gone(response);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const progress = await response.json();
      if (progress.done !== lastDone || progress.state !== lastState) {
        const results = await fetch(`/batches/${id}/results`, { cache: "no-store" });
        if (results.status === 404) return gone(results);
        if (!results.ok) throw new Error(`HTTP ${results.status}`);
        lastDone = progress.done;
        lastState = progress.state;
        const open = [...document.querySelectorAll("details[data-key][open]")].map((d) => d.dataset.key);
        document.getElementById("batch-results").innerHTML = await results.text();
        open.forEach((key) => {
          const details = document.querySelector(`details[data-key="${key}"]`);
          if (details) details.open = true;
        });
        announce.textContent =
          progress.state === "finished"
            ? "The batch is finished."
            : `${progress.done} of ${progress.total} labels checked.`;
      }
      if (failures) {
        failures = 0;
        show("");
      }
      if (progress.state !== "finished") setTimeout(update, 2000);
    } catch {
      failures += 1;
      show(
        failures < 10
          ? "Lost contact with the app. Reconnecting…"
          : "Still reconnecting. The batch keeps running on the server, and this page updates when the connection is back."
      );
      setTimeout(update, Math.min(2000 * 2 ** (failures - 1), 15000));
    }
  };
  setTimeout(update, 1000);
}
