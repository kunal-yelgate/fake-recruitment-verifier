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

function createRequestContext(signal, timeoutMs) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const abortRequest = () => controller.abort();

  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener("abort", abortRequest, { once: true });
    }
  }

  return {
    signal: controller.signal,
    cleanup() {
      clearTimeout(timeoutId);
      signal?.removeEventListener("abort", abortRequest);
    },
  };
}

async function getErrorMessage(response, fallback) {
  try {
    const errorBody = await response.json();
    if (typeof errorBody.detail === "string" && errorBody.detail) {
      return errorBody.detail;
    }
  } catch {
    // Keep the endpoint-specific fallback when the error response is not JSON.
  }
  return fallback;
}

/**
 * Submits raw posting text to FastAPI /check endpoint with timeout protection.
 * @param {string} rawText
 * @param {AbortSignal} [signal]
 * @param {string} [token]
 * @returns {Promise<object>}
 */
export async function verifyPosting(rawText, signal, token) {
  const request = createRequestContext(signal, 30000);

  try {
    const response = await fetch(`${API_BASE_URL}/check`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ raw_text: rawText }),
      signal: request.signal,
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response, `Server error (${response.status})`));
    }

    return await response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Verification timed out after 30 seconds. Please check your backend connection.");
    }
    throw error;
  } finally {
    request.cleanup();
  }
}

/**
 * Fetch bounded text from a public job-posting URL.
 * @param {string} url
 * @param {AbortSignal} [signal]
 * @param {string} [token]
 * @returns {Promise<{text: string, final_url: string, content_type: string}>}
 */
export async function fetchJobUrl(url, signal, token) {
  const request = createRequestContext(signal, 15000);

  try {
    const response = await fetch(`${API_BASE_URL}/fetch-url`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ url }),
      signal: request.signal,
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response, `Unable to fetch URL (${response.status})`));
    }

    return await response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("URL fetch timed out. Please paste the posting text instead.");
    }
    throw error;
  } finally {
    request.cleanup();
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
