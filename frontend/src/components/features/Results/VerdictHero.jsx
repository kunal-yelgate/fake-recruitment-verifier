import React from "react";
import { AlertOctagon, CheckCircle2, AlertTriangle, ShieldAlert, Share2, FileText, Info } from "lucide-react";
import { ProgressRing } from "../../ui/ProgressRing";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";

export function VerdictHero({
  score,
  verdict,
  verdictBadge,
  summary,
  groqDecision,
  isMock,
  hasSearchError,
  executionTime,
  onOpenExport,
}) {
  const isPass = verdictBadge === "success" || score < 35;
  const isFail = verdictBadge === "danger" || score >= 65;

  const containerTheme = isPass
    ? "bg-gradient-to-br from-emerald-950/40 via-slate-900/80 to-slate-950/90 border-emerald-500/30 text-emerald-100"
    : isFail
    ? "bg-gradient-to-br from-rose-950/40 via-slate-900/80 to-slate-950/90 border-rose-500/30 text-rose-100"
    : "bg-gradient-to-br from-amber-950/40 via-slate-900/80 to-slate-950/90 border-amber-500/30 text-amber-100";

  const badgeVariant = isPass ? "success" : isFail ? "danger" : "warning";
  const Icon = isPass ? CheckCircle2 : isFail ? AlertOctagon : AlertTriangle;

  return (
    <div
      className={`rounded-2xl border p-6 sm:p-8 flex flex-col md:flex-row items-center gap-6 sm:gap-8 shadow-2xl backdrop-blur-xl transition-all duration-300 ${containerTheme}`}
    >
      {/* Radial score gauge */}
      <div className="flex-shrink-0">
        <ProgressRing score={score} size={130} strokeWidth={10} />
      </div>

      {/* Narrative & Verdict Breakdown */}
      <div className="flex-1 text-center md:text-left space-y-3">
        <div className="flex flex-wrap items-center justify-center md:justify-start gap-2.5">
          <Badge variant={badgeVariant} size="md" icon={Icon}>
            {verdict}
          </Badge>

          {executionTime && (
            <span className="text-[11px] font-mono text-slate-400 dark:text-slate-400 bg-slate-800/60 px-2.5 py-0.5 rounded-full border border-slate-700/60">
              ⚡ {executionTime}s analysis
            </span>
          )}
        </div>

        <h3 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
          {isFail
            ? "Critical Recruitment Risk Detected"
            : isPass
            ? "Authentic Corporate Footprint Verified"
            : "Caution: Uncorroborated Recruitment Signals"}
        </h3>

        <p className="text-xs sm:text-sm text-slate-300 dark:text-slate-300 leading-relaxed max-w-2xl font-sans">
          {summary}
        </p>

        {groqDecision && (
          <div className="max-w-2xl border-t border-white/15 pt-4 text-left">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-orange-300">
              Groq second opinion · does not change the score
            </p>
            <p className="mt-2 text-sm font-semibold text-white">
              {{
                avoid_contact: "Avoid contact for now",
                verify_independently: "Verify independently before proceeding",
                no_clear_warning_found: "No clear warning found in the available evidence",
              }[groqDecision.recommendation] || "Verify independently before proceeding"}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-slate-300">
              {groqDecision.explanation}
            </p>
            <ul className="mt-2 space-y-1">
              {groqDecision.evidence_quotes.map((quote, index) => (
                <li key={`${quote}-${index}`} className="border-l-2 border-orange-300/70 pl-2 text-[11px] italic text-slate-300">
                  “{quote}”
                </li>
              ))}
            </ul>
          </div>
        )}

        {isMock && (
          <div className="inline-flex items-center gap-1.5 text-xs text-amber-300 bg-amber-400/10 px-3 py-1.5 rounded-lg border border-amber-400/20">
            <Info className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Demo mode: simulated search results are not live evidence.</span>
          </div>
        )}

        {hasSearchError && (
          <div className="inline-flex items-center gap-1.5 text-xs text-amber-200 bg-amber-400/10 px-3 py-1.5 rounded-lg border border-amber-400/20">
            <Info className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Some searches failed. Those checks were excluded from scoring.</span>
          </div>
        )}

        {/* Action Toolbar */}
        <div className="pt-2 flex flex-wrap items-center justify-center md:justify-start gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenExport}
            className="bg-white/10 hover:bg-white/20 text-white border-white/20"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Export Forensic Report</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
