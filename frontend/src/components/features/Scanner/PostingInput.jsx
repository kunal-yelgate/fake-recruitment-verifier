import React, { useRef } from "react";
import {
  AlertTriangle,
  ArrowRight,
  RotateCcw,
  UploadCloud,
  Search,
} from "lucide-react";
import { Button } from "../../ui/Button";
import { Card } from "../../ui/Card";
import { ScanProgressStepper } from "./ScanProgressStepper";

export function PostingInput({
  text,
  setText,
  onVerify,
  isLoading,
  error,
  scanSteps,
  activeStepIndex,
}) {
  const fileInputRef = useRef(null);
  const charCount = text.trim().length;
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result;
      if (typeof content === "string") {
        setText(content);
      }
    };
    reader.readAsText(file);
  };

  return (
    <Card className="space-y-6 rounded-[32px] border-[#d1cdc7]/70 p-5 shadow-[0_24px_48px_rgba(20,20,19,0.06)] sm:p-7 dark:border-white/10">
      {/* Header title */}
      <div>
        <div className="mb-2 flex items-center gap-2">
          <Search className="h-5 w-5 text-[#cf4500] dark:text-[#f37338]" />
          <span className="text-xs font-bold uppercase tracking-[0.18em] text-[#cf4500] dark:text-[#f37338]">
            Recruiter check
          </span>
        </div>
        <h2 className="text-2xl font-medium tracking-tight text-[#141413] dark:text-[#f3f0ee] sm:text-3xl">
          Analyze the message you received.
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-[#696969] dark:text-[#d1cdc7]">
          Results are based only on the information you provide. We flag identity gaps, suspicious requests, and critical scam signals.
        </p>
      </div>

      {/* Textarea Input Container */}
      <div className="space-y-2">
        <div className="relative">
          <textarea
            rows={7}
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={isLoading}
            placeholder="Paste the job post, recruiter email, or direct message you want analyzed..."
            className="min-h-[180px] w-full resize-y rounded-[20px] border border-[#d1cdc7] bg-[#fcfbfa] p-4 font-mono text-xs leading-relaxed text-[#141413] shadow-inner transition placeholder:text-[#96918a] focus:border-[#141413] focus:outline-none focus:ring-2 focus:ring-[#141413]/10 dark:border-white/15 dark:bg-[#141413]/70 dark:text-[#f3f0ee] dark:placeholder:text-[#696969] dark:focus:border-[#f3f0ee] sm:text-sm"
          />

          {/* Hidden File Input for drag/upload */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".txt,.md,.eml"
            className="hidden"
          />
        </div>

        {/* Live Scan Step Stepper if loading */}
        {isLoading && (
          <div className="pt-2">
            <ScanProgressStepper
              steps={scanSteps}
              activeIndex={activeStepIndex}
            />
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="flex items-center gap-2.5 rounded-[20px] border border-[#cf4500]/25 bg-[#cf4500]/10 p-3.5 text-xs text-[#9a3a0a] animate-in fade-in duration-200 dark:text-[#f37338]">
            <AlertTriangle className="h-4 w-4 flex-shrink-0 text-[#cf4500] dark:text-[#f37338]" />
            <span className="font-medium">{error}</span>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="flex flex-col items-center justify-between gap-4 border-t border-[#d1cdc7]/70 pt-4 sm:flex-row dark:border-white/10">
        <div className="order-2 flex items-center gap-3 font-mono text-xs text-[#696969] dark:text-[#d1cdc7] sm:order-1">
          <span>{charCount.toLocaleString()} chars</span>
          <span>•</span>
          <span>{wordCount.toLocaleString()} words</span>
          {text && (
            <>
              <span>•</span>
              <button
                type="button"
                onClick={() => setText("")}
                disabled={isLoading}
                className="inline-flex cursor-pointer items-center gap-1 text-[#696969] transition-colors hover:text-[#141413] dark:hover:text-white"
              >
                <RotateCcw className="w-3 h-3" />
                Clear
              </button>
            </>
          )}
        </div>

        <div className="order-1 flex w-full items-center gap-2.5 sm:order-2 sm:w-auto">
          <Button
            type="button"
            variant="outline"
            size="md"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="w-full sm:w-auto"
            title="Upload text file"
          >
            <UploadCloud className="w-4 h-4" />
            <span className="hidden sm:inline">Upload .txt</span>
          </Button>

          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={onVerify}
            isLoading={isLoading}
            disabled={isLoading || charCount < 10}
            className="w-full sm:w-auto"
          >
            <span>Run OSINT Verification</span>
            <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
