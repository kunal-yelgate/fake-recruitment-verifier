const DEFAULT_API_URL = "http://127.0.0.1:8000/check";
const MENU_ID = "check-selected-recruiter-text";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: MENU_ID,
      title: "Check selected text with Fake Recruiter Verifier",
      contexts: ["selection"]
    });
  });
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== MENU_ID || !info.selectionText?.trim()) return;

  try {
    const result = await checkText(info.selectionText);
    await chrome.storage.local.set({ lastResult: result });
    setActionBadge(result);
    showNotification(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Verification failed.";
    await chrome.storage.local.set({ lastError: message });
    chrome.action.setBadgeText({ text: "!" });
    chrome.action.setBadgeBackgroundColor({ color: "#b42318" });
    showNotification({ verdict: "Verification failed", summary: message });
  }
});

async function checkText(rawText) {
  const { apiUrl = DEFAULT_API_URL } = await chrome.storage.sync.get({ apiUrl: DEFAULT_API_URL });
  const endpoint = normalizeEndpoint(apiUrl);
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_text: rawText.trim() })
  });

  if (!response.ok) {
    throw new Error(`API request failed (${response.status}).`);
  }
  return response.json();
}

function normalizeEndpoint(value) {
  const endpoint = String(value).trim().replace(/\/+$/, "");
  if (!endpoint) throw new Error("Configure an API endpoint in extension options.");
  return endpoint.endsWith("/check") ? endpoint : `${endpoint}/check`;
}

function setActionBadge(result) {
  const colors = { danger: "#b42318", warning: "#b54708", success: "#027a48" };
  const badge = String(result.verdict_badge || "warning");
  chrome.action.setBadgeText({ text: badge === "success" ? "OK" : "!" });
  chrome.action.setBadgeBackgroundColor({ color: colors[badge] || colors.warning });
}

function showNotification(result) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icon.svg",
    title: result.verdict || "Verification result",
    message: result.summary || "Open the extension popup for details."
  });
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "checkText") return;
  checkText(message.text)
    .then(async (result) => {
      await chrome.storage.local.set({ lastResult: result, lastError: "" });
      setActionBadge(result);
      sendResponse({ result });
    })
    .catch(async (error) => {
      const messageText = error instanceof Error ? error.message : "Verification failed.";
      await chrome.storage.local.set({ lastError: messageText });
      sendResponse({ error: messageText });
    });
  return true;
});
