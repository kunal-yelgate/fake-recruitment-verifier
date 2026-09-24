import { useState, useCallback, useRef } from "react";
import { verifyPosting } from "../services/api";

const SCAN_STEPS = [
  { id: "message", label: "Reading the message for key details", duration: 350 },
  { id: "company", label: "Checking the company identity", duration: 450 },
  { id: "recruiter", label: "Checking recruiter and contact details", duration: 450 },
  { id: "patterns", label: "Looking for copied or known scam patterns", duration: 500 },
  { id: "warnings", label: "Checking public warnings and risk signals", duration: 400 },
  { id: "verdict", label: "Calculating the risk and safety result", duration: 450 },
];

export function useVerifier(onSuccess) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [activeStepIndex, setActiveStepIndex] = useState(0);

  const abortControllerRef = useRef(null);

  const verify = useCallback(
    async (text) => {
      if (!text || text.trim().length < 10) {
        setError("Please enter at least 10 characters from the job posting or recruiter message.");
        return;
      }

      setError(null);
      setIsLoading(true);
      setActiveStepIndex(0);

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      // Start sequential step animator
      let currentStep = 0;
      const stepTimer = setInterval(() => {
        currentStep++;
        if (currentStep < SCAN_STEPS.length) {
          setActiveStepIndex(currentStep);
        }
      }, 400);

      try {
        const data = await verifyPosting(text.trim(), abortControllerRef.current.signal);
        clearInterval(stepTimer);
        setActiveStepIndex(SCAN_STEPS.length - 1);
        setResults(data);
        if (onSuccess) {
          onSuccess(data, text);
        }
      } catch (err) {
        clearInterval(stepTimer);
        console.error("Verification failed:", err);
        setError(err.message || "Failed to contact verification server.");
      } finally {
        setIsLoading(false);
      }
    },
    [onSuccess]
  );

  const reset = useCallback(() => {
    setResults(null);
    setError(null);
    setIsLoading(false);
    setActiveStepIndex(0);
  }, []);

  return {
    verify,
    reset,
    results,
    setResults,
    isLoading,
    error,
    activeStepIndex,
    scanSteps: SCAN_STEPS,
  };
}
