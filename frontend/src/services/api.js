const envApiUrl = import.meta.env.VITE_API_BASE_URL;

export const API_BASE_URL =
  envApiUrl && envApiUrl.trim() !== ""
    ? envApiUrl.replace(/\/+$/, "")
    : typeof window !== "undefined" &&
      (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? window.location.port === "8000"
      ? ""
      : "http://127.0.0.1:8000"
    : "";

/**
 * Submits raw posting text to FastAPI /check endpoint with timeout protection.
 * @param {string} rawText
 * @param {AbortSignal} [signal]
 * @returns {Promise<object>}
 */
export async function verifyPosting(rawText, signal) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

  try {
    const response = await fetch(`${API_BASE_URL}/check`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ raw_text: rawText }),
      signal: signal || controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMsg = `Server error (${response.status})`;
      try {
        const errJson = await response.json();
        if (errJson.detail) errorMsg = errJson.detail;
      } catch {
        // ignore JSON parse error
      }
      throw new Error(errorMsg);
    }

    return await response.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      throw new Error("Verification timed out after 30 seconds. Please check your backend connection.");
    }
    throw err;
  }
}

/**
 * Checks backend health and cache metrics.
 * @returns {Promise<object>}
 */
export async function getBackendStatus() {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, { method: "GET" });
    if (!res.ok) return { online: false };
    const data = await res.json();
    return { online: true, ...data };
  } catch {
    return { online: false };
  }
}
