import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE_URL, fetchJobUrl, verifyPosting } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("backend API client", () => {
  it("sends authenticated posting checks to the configured backend", async () => {
    const result = { risk_score: 25 };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => result,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(verifyPosting("A job posting", undefined, "session-token")).resolves.toEqual(result);

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/check`,
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer session-token",
        }),
        body: JSON.stringify({ raw_text: "A job posting" }),
      })
    );
  });

  it("keeps URL import requests at module scope and sends the session token", async () => {
    const result = { text: "Job description", final_url: "https://jobs.example.test", content_type: "text/html" };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => result,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchJobUrl("https://jobs.example.test", undefined, "session-token")).resolves.toEqual(result);

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/fetch-url`,
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer session-token",
        }),
        body: JSON.stringify({ url: "https://jobs.example.test" }),
      })
    );
  });

  it("surfaces API response details when a posting check fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ detail: "Authentication is not configured on this server." }),
      })
    );

    await expect(verifyPosting("A job posting")).rejects.toThrow(
      "Authentication is not configured on this server."
    );
  });
});
