import React from "react";
import {
  AlertOctagon,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Share2,
  FileText,
  Info,
  ExternalLink,
  Users,
} from "lucide-react";
import { ProgressRing } from "../../ui/ProgressRing";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";

export function VerdictHero({
  score,
  verdict,
  verdictBadge,
  summary,
  groqDecision,
  claimAudit,
  linkedinReferralLeads = [],
  isMock,
  dataQuality = "demo",
  hasSearchError,
  executionTime,
  onOpenExport,
}) {
  const isLive = dataQuality === "live";
  const isPass = isLive && (verdictBadge === "success" || score < 35);
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
        {dataQuality !== "live" && (
          <div className="rounded-xl border border-amber-300/50 bg-amber-300/15 px-4 py-3 text-left text-sm font-semibold text-amber-100">
            This result uses {dataQuality === "demo" ? "demo or unavailable" : "partial"} data.
            It is not a real verdict; verify the employer independently.
          </div>
        )}
        <div className="flex flex-wrap items-center justify-center md:justify-start gap-2.5">
          <Badge variant={badgeVariant} size="md" icon={Icon}>
            {isLive ? verdict : "Demo result, not a real verdict"}
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
              Groq recommendation · separate from the risk score
            </p>
            <p className="mt-2 text-sm font-semibold text-white">
              {{
                apply:
                  "Apply after confirming the listing on the official careers site",
                do_not_apply: "Do not apply based on the strong warning signs",
                verify_before_applying:
                  "Verify the employer and role before applying",
              }[groqDecision.recommendation] ||
                "Verify independently before proceeding"}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-slate-300">
              {groqDecision.explanation}
            </p>
            <ul className="mt-2 space-y-1">
              {groqDecision.evidence_quotes.map((quote, index) => (
                <li
                  key={`${quote}-${index}`}
                  className="border-l-2 border-orange-300/70 pl-2 text-[11px] italic text-slate-300"
                >
                  “{quote}”
                </li>
              ))}
            </ul>

            {groqDecision.recommendation === "apply" &&
              linkedinReferralLeads.length > 0 && (
                <div className="mt-4 rounded-xl border border-sky-400/20 bg-sky-400/5 p-3">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-sky-200">
                    <Users className="h-3.5 w-3.5" />
                    Possible referral leads
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-slate-400">
                    These are public search matches that may help you ask for a
                    referral. Confirm the person’s current role and connection
                    to the company before contacting them.
                  </p>
                  <div className="mt-3 space-y-2">
                    {linkedinReferralLeads.map((lead) => (
                      <a
                        key={lead.profile_url}
                        href={lead.profile_url}
                        target="_blank"
                        rel="noreferrer"
                        className="group block rounded-lg border border-white/10 bg-slate-950/30 p-2.5 transition-colors hover:border-sky-300/40 hover:bg-sky-300/10"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <span className="text-xs font-semibold text-white">
                            {lead.name}
                          </span>
                          <ExternalLink className="h-3.5 w-3.5 flex-shrink-0 text-sky-300 opacity-70 group-hover:opacity-100" />
                        </div>
                        {lead.headline && (
                          <p className="mt-1 text-[11px] leading-relaxed text-slate-400">
                            {lead.headline}
                          </p>
                        )}

                        {claimAudit?.explanation && (
                          <div className="max-w-2xl border-t border-white/15 pt-4 text-left">
                            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-indigo-300">
                              Cited analysis
                            </p>
                            <p className="mt-2 text-xs leading-relaxed text-slate-300">
                              {claimAudit.explanation.text}
                            </p>
                            {claimAudit.explanation.citations?.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-2">
                                {claimAudit.explanation.citations.map((citation) => (
                                  <a
                                    key={citation}
                                    href={citation}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="max-w-full truncate text-[11px] text-indigo-300 underline decoration-indigo-300/40 hover:text-indigo-200"
                                  >
                                    Source: {citation}
                                  </a>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </a>
                    ))}
                  </div>
                </div>
              )}
          </div>
        )}

        {isMock && (
          <div className="inline-flex items-center gap-1.5 text-xs text-amber-300 bg-amber-400/10 px-3 py-1.5 rounded-lg border border-amber-400/20">
            <Info className="w-3.5 h-3.5 flex-shrink-0" />
            <span>
              Demo mode: simulated search results are not live evidence.
            </span>
          </div>
        )}

        {hasSearchError && (
          <div className="inline-flex items-center gap-1.5 text-xs text-amber-200 bg-amber-400/10 px-3 py-1.5 rounded-lg border border-amber-400/20">
            <Info className="w-3.5 h-3.5 flex-shrink-0" />
            <span>
              Some searches failed. Those checks were excluded from scoring.
            </span>
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
