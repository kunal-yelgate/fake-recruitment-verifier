const DEFAULT_API_URL = "http://127.0.0.1:8000/check";
const input = document.querySelector("#api-url");
const status = document.querySelector("#status");

chrome.storage.sync.get({ apiUrl: DEFAULT_API_URL }, ({ apiUrl }) => {
  input.value = apiUrl;
});

document.querySelector("#save").addEventListener("click", async () => {
  const apiUrl = input.value.trim();
  if (!apiUrl) {
    status.textContent = "Enter an API URL.";
    return;
  }
  try {
    const parsed = new URL(apiUrl);
    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw new Error("unsupported protocol");
    }
  } catch {
    status.textContent = "Enter a valid URL.";
    return;
  }
  await chrome.storage.sync.set({ apiUrl });
  status.textContent = "Saved.";
});
