import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "jobguard_scan_history_v1";
const MAX_HISTORY_ITEMS = 15;

export function useScanHistory() {
  const [history, setHistory] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (e) {
      console.warn("Could not save history to localStorage:", e);
    }
  }, [history]);

  const addScan = useCallback((resultData, rawInputText) => {
    if (!resultData) return;

    const company = resultData.extracted_fields?.company_name || "Unknown Company";
    const role = resultData.extracted_fields?.job_title || "Job Posting";
    const snippet = rawInputText.slice(0, 140).replace(/\s+/g, " ") + "...";

    const newItem = {
      id: crypto.randomUUID(),
      timestamp: Date.now(),
      company,
      role,
      snippet,
      rawText: rawInputText,
      result: resultData,
    };

    setHistory((prev) => {
      // Remove any duplicate of the same company/score combo from top
      const filtered = prev.filter(
        (item) => item.company !== newItem.company || item.result?.risk_score !== newItem.result?.risk_score
      );
      return [newItem, ...filtered].slice(0, MAX_HISTORY_ITEMS);
    });
  }, []);

  const removeScan = useCallback((id) => {
    setHistory((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }, []);

  return {
    history,
    addScan,
    removeScan,
    clearHistory,
    count: history.length,
  };
}
