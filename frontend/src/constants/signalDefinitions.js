import { MapPin, Linkedin, Copy, Newspaper, Globe, UserCheck, ShieldAlert } from "lucide-react";

export const SIGNAL_METADATA = {
  text_threat_signals: {
    label: "In-Posting Threat Patterns",
    engine: "NLP & Forensic Scanner",
    icon: ShieldAlert,
    category: "Forensic Intel",
    color: "red",
    description: "Inspects raw posting text for check deposit traps, Telegram interview redirects, equipment fees, or unrealistic pay."
  },
  company_footprint: {
    label: "Physical Footprint",
    engine: "Google Maps",
    icon: MapPin,
    category: "Footprint",
    color: "emerald",
    description: "Cross-checks registered corporate headquarters, office buildings, and official Google Maps street listings."
  },
  linkedin_presence: {
    label: "Corporate LinkedIn",
    engine: "Google Search (site:linkedin.com)",
    icon: Linkedin,
    category: "Identity",
    color: "blue",
    description: "Verifies company profile, verified employee headcount, and corporate branding."
  },
  duplicate_posting: {
    label: "Global Web Duplication",
    engine: "Google Search (Exact Match)",
    icon: Copy,
    category: "Spam Detection",
    color: "purple",
    description: "Scans for automated duplicate syndication across pastebins, free classifieds, or spam forums."
  },
  news_fraud_mentions: {
    label: "News Fraud Intelligence",
    engine: "Google News",
    icon: Newspaper,
    category: "Threat Intel",
    color: "rose",
    description: "Queries recent media reports, consumer protection alerts (FTC/BBB), and lawsuit records."
  },
  domain_match: {
    label: "Domain & Email Legitimacy",
    engine: "Google Search / MX",
    icon: Globe,
    category: "Domain Security",
    color: "cyan",
    description: "Detects free webmail addresses (@gmail, @yahoo) and flags lookalike impostor domains."
  },
  recruiter_check: {
    label: "Recruiter Affiliation",
    engine: "Google Search",
    icon: UserCheck,
    category: "Identity",
    color: "amber",
    description: "Verifies recruiter name, professional public presence, and verified affiliation with the hiring company."
  }
};
