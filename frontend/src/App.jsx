import React, { useState, useEffect, useRef } from "react";
import { Navbar } from "./components/layouts/Navbar";
import { Footer } from "./components/layouts/Footer";
import { PostingInput } from "./components/features/Scanner/PostingInput";
import { VerdictHero } from "./components/features/Results/VerdictHero";
import { ThreatRadar } from "./components/features/Results/ThreatRadar";
import { SafetyChecklist } from "./components/features/Results/SafetyChecklist";
import { ExportReportModal } from "./components/features/Results/ExportReportModal";
import { EntitiesGrid } from "./components/features/Entities/EntitiesGrid";
import { EvidenceTable } from "./components/features/Evidence/EvidenceTable";
import { ScanHistoryDrawer } from "./components/features/History/ScanHistoryDrawer";
import { useVerifier } from "./hooks/useVerifier";
import { useScanHistory } from "./hooks/useScanHistory";
import { getBackendStatus } from "./services/api";
import { LandingPage } from "./components/LandingPage";

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem("theme");
    return saved ? saved === "dark" : true;
  });

  const [text, setText] = useState("");
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [backendHealth, setBackendHealth] = useState({ online: true });

  const resultsRef = useRef(null);
  const {
    history,
    addScan,
    removeScan,
    clearHistory,
    count: historyCount,
  } = useScanHistory();

  // Initialize verifier hook
  const {
    verify,
    results,
    setResults,
    isLoading,
    error,
    activeStepIndex,
    scanSteps,
  } = useVerifier((data, rawText) => {
    addScan(data, rawText);
    setTimeout(() => {
      resultsRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 150);
  });

  // Handle theme toggle
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      root.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [isDark]);

  // Check health periodically
  useEffect(() => {
    getBackendStatus().then(setBackendHealth);
  }, []);

  const handleVerify = () => {
    verify(text);
  };

  const handleSelectHistoryScan = (historyItem) => {
    setText(historyItem.rawText || "");
    setResults(historyItem.result);
    setTimeout(() => {
      resultsRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 150);
  };

  const isPass = results ? results.risk_score < 35 : false;
  const isFail = results ? results.risk_score >= 65 : false;

  if (showLanding) {
    return (
      <LandingPage
        isDark={isDark}
        onToggleTheme={() => setIsDark((prev) => !prev)}
        onEnter={() => setShowLanding(false)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#f3f0ee] text-[#141413] selection:bg-[#cf4500] selection:text-white transition-colors duration-200 flex flex-col justify-between dark:bg-[#141413] dark:text-[#f3f0ee]">
      {/* Top Navigation Bar */}
      <Navbar
        isDark={isDark}
        onToggleTheme={() => setIsDark((prev) => !prev)}
        onOpenHistory={() => setIsHistoryOpen(true)}
        historyCount={historyCount}
        isBackendConnected={backendHealth.online}
        isMockMode={results?.is_mock}
      />

      {/* Main Content Area */}
      <main className="max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 flex-1">
        {/* Scanner Input Console */}
        <PostingInput
          text={text}
          setText={setText}
          onVerify={handleVerify}
          isLoading={isLoading}
          error={error}
          scanSteps={scanSteps}
          activeStepIndex={activeStepIndex}
        />

        {/* Forensic Results Section */}
        {results && (
          <div
            ref={resultsRef}
            className="space-y-6 pt-4 animate-in fade-in slide-in-from-bottom-4 duration-500"
          >
            {/* Verdict Hero Banner */}
            <VerdictHero
              score={results.risk_score}
              verdict={results.verdict}
              verdictBadge={results.verdict_badge}
              summary={results.summary}
              isMock={results.is_mock}
              executionTime={results.execution_time_seconds}
              onOpenExport={() => setIsExportOpen(true)}
            />

            {/* Extracted Entities Grid */}
            <EntitiesGrid extractedFields={results.extracted_fields} />

            {/* 2-Column Insight Panels: Threat Radar & Safety Advisory */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ThreatRadar signals={results.signals} />
              <SafetyChecklist
                score={results.risk_score}
                isFail={isFail}
                isPass={isPass}
              />
            </div>

            {/* Comprehensive OSINT Evidence Matrix */}
            <EvidenceTable signals={results.signals} />
          </div>
        )}
      </main>

      {/* Footer */}
      <Footer />

      {/* Slide-out Scan History Drawer */}
      <ScanHistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={history}
        onSelectScan={handleSelectHistoryScan}
        onRemoveScan={removeScan}
        onClearHistory={clearHistory}
      />

      {/* Export Report Modal */}
      <ExportReportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        results={results}
      />
    </div>
  );
}
