# Fake Recruiter Verifier browser extension

This is a minimal Manifest V3 extension for Chrome-compatible browsers.

## Configuration

1. Start the backend, or deploy a compatible `POST /check` API.
2. Load this folder as an unpacked extension from `chrome://extensions`.
3. Open **Details > Extension options** and set the API base URL or full `/check` endpoint.
4. Select recruiter or job-posting text on any page and choose **Check selected text with Fake Recruiter Verifier**, or open the toolbar popup and paste text.

The extension sends only `{ "raw_text": "..." }`. It contains no API keys, tokens, or other secrets. The endpoint URL is stored in `chrome.storage.sync`.

## Permissions

- `contextMenus`: adds the selected-text check action.
- `notifications`: shows the result of a context-menu check.
- `storage`: stores the configured endpoint and most recent result.
- `http://localhost:8000/*` and `http://127.0.0.1:8000/*`: allow the default local API request.

If the API is hosted elsewhere, add its origin to `host_permissions` in `manifest.json` before loading the extension. The API must permit requests from the extension origin with CORS; do not put credentials in this extension.

The API response should include `verdict`, `verdict_badge` (`danger`, `warning`, or `success`), `risk_score`, and `summary`.
