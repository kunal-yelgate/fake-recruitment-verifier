import React from "react";
import { CheckCircle2, Loader2, Radio } from "lucide-react";

export function ScanProgressStepper({ steps, activeIndex }) {
  return (
    <div className="rounded-[24px] border border-[#f37338]/30 bg-[#141413]/95 p-4 text-[#f3f0ee] shadow-2xl backdrop-blur-md animate-in fade-in zoom-in-95 duration-200">
      <div className="mb-3 flex items-center justify-between border-b border-white/10 pb-3">
        <div className="flex items-center gap-2">
          <div className="h-2.5 w-2.5 rounded-full bg-[#f37338] animate-ping" />
          <span className="text-xs font-bold uppercase tracking-[0.14em] text-[#f37338]">
            Analysis in progress
          </span>
        </div>
        <span className="font-mono text-xs text-[#d1cdc7]">
          Check {Math.min(activeIndex + 1, steps.length)} of {steps.length}
        </span>
      </div>

      <p className="mb-3 text-xs leading-relaxed text-[#d1cdc7]">We are checking the details you provided before giving a safety result.</p>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {steps.map((step, idx) => {
          const isDone = idx < activeIndex;
          const isCurrent = idx === activeIndex;

          let stateStyle = "border-white/10 bg-white/5 text-[#96918a] opacity-60";
          if (isCurrent) {
            stateStyle =
              "border-[#f37338]/60 bg-[#cf4500]/15 text-[#f3f0ee] shadow-md shadow-[#cf4500]/20";
          } else if (isDone) {
            stateStyle = "border-emerald-500/40 bg-emerald-950/40 text-emerald-300";
          }

          return (
            <div
              key={step.id}
              className={`flex items-center gap-2 rounded-[14px] border p-2.5 text-xs transition-all duration-300 ${stateStyle}`}
            >
              {isDone ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              ) : isCurrent ? (
                <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-[#f37338]" />
              ) : (
                <Radio className="h-4 w-4 flex-shrink-0 text-[#696969]" />
              )}
              <span className="font-medium truncate">{step.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
