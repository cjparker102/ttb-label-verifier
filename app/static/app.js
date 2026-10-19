// Small helpers. The page works without them.
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("check-form");
  if (form) {
    form.addEventListener("submit", () => {
      const button = document.getElementById("check-button");
      button.disabled = true;
      button.textContent = "Checking…";
      document.getElementById("busy").hidden = false;
    });
  }

  // After a check, move keyboard and screen-reader focus to what changed.
  const target = document.getElementById("errors") || document.getElementById("results-heading");
  if (target) {
    target.focus();
  }
});
