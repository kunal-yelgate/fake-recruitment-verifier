import React from "react";
import {
  Building2,
  Briefcase,
  UserCheck,
  Globe,
  Quote,
  Cpu,
  DollarSign,
  CreditCard,
} from "lucide-react";
import { Card } from "../../ui/Card";
import { DomainMismatchAlert } from "./DomainMismatchAlert";

export function EntitiesGrid({ extractedFields }) {
  if (!extractedFields) return null;

  const entities = [
    {
      label: "Hiring Entity / Company",
      value: extractedFields.company_name || "Unspecified Organization",
      icon: Building2,
      sub: "Corroborated across Maps & LinkedIn",
    },
    {
      label: "Target Role & Title",
      value: extractedFields.job_title || "Unspecified Role",
      icon: Briefcase,
      sub: "Extracted via NLP heuristic parser",
    },
    {
      label: "Named Recruiter / Agent",
      value: extractedFields.recruiter_name || "No individual named",
      icon: UserCheck,
      sub: "Verified against professional records",
    },
    {
      label: "Claimed Domain / Email",
      value: extractedFields.contact_email || extractedFields.claimed_domain || "None listed",
      icon: Globe,
      sub: extractedFields.claimed_domain ? `Domain: ${extractedFields.claimed_domain}` : "No domain",
    },
    {
      label: "Salary / Compensation",
      value: extractedFields.salary_range || "Not stated",
      icon: DollarSign,
      sub: "Copied from the supplied posting",
    },
  ];

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-indigo-500" />
          <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
            Extracted Entity Credentials
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
          Extraction: {extractedFields.extraction_method || "Regex + Heuristics"}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {entities.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-50/80 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 flex flex-col justify-between space-y-2 hover:border-indigo-500/30 transition-colors"
            >
              <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-xs font-semibold">
                <Icon className="w-4 h-4 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
                <span className="truncate">{item.label}</span>
              </div>

              <div
                className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate"
                title={item.value}
              >
                {item.value}
              </div>

              <div className="text-[10px] text-slate-400 dark:text-slate-500 truncate font-mono">
                {item.sub}
              </div>
            </div>
          );
        })}
      </div>

      {extractedFields.payment_requests?.length > 0 && (
        <div className="p-3.5 rounded-xl bg-rose-50/80 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/60 text-xs flex items-start gap-2.5">
          <CreditCard className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <span className="font-bold text-rose-700 dark:text-rose-300">
              Payment requests found:{" "}
            </span>
            <span className="text-rose-700/80 dark:text-rose-200/80">
              {extractedFields.payment_requests.join(" • ")}
            </span>
          </div>
        </div>
      )}

      {/* Free webmail alert if present */}
      <DomainMismatchAlert
        claimedDomain={extractedFields.claimed_domain}
        contactEmail={extractedFields.contact_email}
      />

      {/* Distinctive Phrase Fingerprint */}
      {extractedFields.distinctive_phrase && (
        <div className="p-3.5 rounded-xl bg-slate-100/80 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800/80 text-xs flex items-start gap-2.5">
          <Quote className="w-4 h-4 text-indigo-500 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-slate-700 dark:text-slate-300">
              Extracted Syndication Fingerprint:{" "}
            </span>
            <span className="font-mono text-slate-600 dark:text-slate-400 italic">
              "{extractedFields.distinctive_phrase}"
            </span>
          </div>
        </div>
      )}
    </Card>
  );
}
