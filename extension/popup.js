const text = document.querySelector("#text");
const checkButton = document.querySelector("#check");
const status = document.querySelector("#status");
const resultSection = document.querySelector("#result");

checkButton.addEventListener("click", () => {
  const rawText = text.value.trim();
  if (!rawText) {
    status.textContent = "Enter text to check.";
    return;
  }

  checkButton.disabled = true;
  status.textContent = "Checking...";
  chrome.runtime.sendMessage({ type: "checkText", text: rawText }, (response) => {
    checkButton.disabled = false;
    if (chrome.runtime.lastError || response?.error) {
      status.textContent = response?.error || chrome.runtime.lastError.message;
      return;
    }
    status.textContent = "";
    renderResult(response.result);
  });
});

chrome.storage.local.get(["lastResult", "lastError"], ({ lastResult, lastError }) => {
  if (lastResult) renderResult(lastResult);
  if (lastError) status.textContent = lastError;
});

function renderResult(result) {
  const badge = String(result.verdict_badge || "warning");
  const badgeElement = document.querySelector("#badge");
  badgeElement.className = `badge ${badge}`;
  badgeElement.textContent = badge;
  document.querySelector("#verdict").textContent = result.verdict || "Unverified";
  document.querySelector("#score").textContent =
    Number.isFinite(result.risk_score) ? `Risk score: ${result.risk_score}/100` : "";
  document.querySelector("#summary").textContent = result.summary || "";
  resultSection.hidden = false;
}
