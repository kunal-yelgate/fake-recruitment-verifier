import React from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  FileWarning,
  Globe2,
  ScanSearch,
  ShieldCheck,
} from "lucide-react";

export function LandingPage({ onEnter, isDark, onToggleTheme }) {
  return (
    <div className="relative isolate min-h-screen overflow-hidden bg-[#f3f0ee] text-[#141413] dark:bg-[#141413] dark:text-[#f3f0ee]">
      <div className="pointer-events-none absolute inset-0 -z-10 opacity-80 dark:opacity-100">
        <div className="absolute -left-32 top-16 h-80 w-80 rounded-full bg-[#f37338]/10 blur-3xl" />
        <div className="absolute right-[-8rem] top-[-7rem] h-[30rem] w-[30rem] rounded-full border border-[#f37338]/20" />
        <div className="absolute right-[-5rem] top-[-4rem] h-80 w-80 rounded-full border border-[#f37338]/15" />
      </div>

      <header className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-6 sm:px-8 lg:px-12">
        <div className="flex items-center gap-3">
          <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-[#141413] text-[#f3f0ee] shadow-[0_4px_24px_rgba(20,20,19,0.12)] dark:bg-[#f3f0ee] dark:text-[#141413]">
            <ShieldCheck className="h-5 w-5" />
            <span className="absolute -right-1 top-0 h-4 w-4 rounded-full bg-[#f37338]" />
          </div>
          <div>
            <p className="text-sm font-bold tracking-[0.16em]">TRUERECRUIT</p>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#696969] dark:text-[#d1cdc7]">
              Recruiter intelligence
            </p>
          </div>
        </div>
        <nav className="hidden items-center gap-7 text-sm font-medium text-[#555555] md:flex dark:text-[#d1cdc7]">
          <a
            href="#how-it-works"
            className="transition hover:text-[#141413] dark:hover:text-white"
          >
            How it works
          </a>
          <a
            href="#signals"
            className="transition hover:text-[#141413] dark:hover:text-white"
          >
            Signals
          </a>
          <button
            type="button"
            onClick={onToggleTheme}
            className="rounded-full border border-[#141413] bg-white/60 px-5 py-2 transition hover:bg-white dark:border-[#f3f0ee] dark:bg-transparent dark:hover:bg-white/10"
            aria-label="Toggle theme"
          >
            {isDark ? "Light view" : "Dark view"}
          </button>
        </nav>
        <button
          type="button"
          onClick={onToggleTheme}
          className="rounded-full border border-[#141413] bg-white/60 px-4 py-2 text-xs md:hidden dark:border-[#f3f0ee] dark:bg-transparent"
          aria-label="Toggle theme"
        >
          {isDark ? "Light" : "Dark"}
        </button>
      </header>

      <main className="mx-auto grid w-full max-w-7xl items-center gap-16 px-5 pb-16 pt-16 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:px-12 lg:pb-28 lg:pt-24">
        <section className="max-w-3xl animate-fade-up">
          <div className="mb-8 inline-flex items-center gap-2 text-[12px] font-bold uppercase tracking-[0.2em] text-[#cf4500] dark:text-[#f37338]">
            <Activity className="h-4 w-4" />
            Verify before you reply
          </div>
          <h1 className="max-w-3xl text-5xl font-medium leading-[0.98] tracking-[-0.035em] sm:text-7xl lg:text-[5.4rem]">
            Is that recruiter real?
            <span className="block text-[#cf4500] dark:text-[#f37338]">
              Find out fast.
            </span>
          </h1>
          <p className="mt-8 max-w-xl text-lg leading-8 text-[#555555] dark:text-[#d1cdc7] sm:text-xl">
            TrueRecruit checks a job posting for suspicious language, mismatched
            domains, missing company footprints, and signals linked to
            recruitment scams.
          </p>
          <div className="mt-9 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={onEnter}
              className="group inline-flex items-center gap-3 rounded-[20px] border border-[#141413] bg-[#141413] px-6 py-3.5 text-base font-medium text-[#f3f0ee] shadow-[0_24px_48px_rgba(20,20,19,0.08)] transition hover:-translate-y-0.5 hover:bg-[#262627] dark:border-[#f3f0ee] dark:bg-[#f3f0ee] dark:text-[#141413] dark:hover:bg-white"
            >
              Scan a recruiter message
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </button>
            <span className="text-xs font-medium uppercase tracking-[0.12em] text-[#696969] dark:text-[#d1cdc7]">
              Paste text. Get a risk score.
            </span>
          </div>
        </section>

        <section
          id="signals"
          className="relative animate-fade-up [animation-delay:120ms]"
        >
          <div className="relative overflow-hidden rounded-[40px] border border-[#141413]/10 bg-[#141413] p-5 text-[#f3f0ee] shadow-[0_24px_48px_rgba(20,20,19,0.08)] dark:border-white/10 dark:bg-[#262627] sm:p-8">
            <div className="absolute -right-16 -top-20 h-56 w-56 rounded-full border border-[#f37338]/40" />
            <div className="absolute -right-5 -top-9 h-32 w-32 rounded-full border border-[#f37338]/30" />
            <div className="relative flex items-center justify-between border-b border-white/15 pb-6">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#f37338]">
                  Threat surface
                </p>
                <p className="mt-2 text-2xl font-medium">
                  A second opinion for your inbox
                </p>
              </div>
              <div className="rounded-full bg-[#f37338] p-3 text-[#141413]">
                <ScanSearch className="h-6 w-6" />
              </div>
            </div>
            <div id="how-it-works" className="relative space-y-3 py-7">
              <div className="flex items-center gap-4 rounded-full border border-white/15 bg-white/5 p-3 pr-5">
                <div className="rounded-full bg-white/10 p-3">
                  <Globe2 className="h-5 w-5 text-[#f37338]" />
                </div>
                <div>
                  <p className="text-sm font-medium">Company footprint</p>
                  <p className="mt-1 text-xs text-[#d1cdc7]">
                    Domain, presence, and identity checks
                  </p>
                </div>
                <CheckCircle2 className="ml-auto h-5 w-5 text-[#f37338]" />
              </div>
              <div className="flex items-center gap-4 rounded-full border border-white/15 bg-white/5 p-3 pr-5">
                <div className="rounded-full bg-white/10 p-3">
                  <FileWarning className="h-5 w-5 text-[#f37338]" />
                </div>
                <div>
                  <p className="text-sm font-medium">Scam patterns</p>
                  <p className="mt-1 text-xs text-[#d1cdc7]">
                    Urgency, payment requests, and copied posts
                  </p>
                </div>
                <span className="ml-auto rounded-full bg-[#f37338]/15 px-2 py-1 font-mono text-[10px] text-[#f37338]">
                  CHECK
                </span>
              </div>
            </div>
            <div className="relative flex items-end justify-between rounded-[24px] bg-[#f3f0ee] p-5 text-[#141413]">
              <div>
                <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-[#696969]">
                  Output
                </p>
                <p className="mt-1 text-3xl font-medium">Risk score</p>
              </div>
              <p className="text-5xl font-medium tracking-[-0.04em]">0-100</p>
            </div>
          </div>
          <p className="mt-5 text-center text-xs font-bold uppercase tracking-[0.16em] text-[#696969] dark:text-[#d1cdc7]">
            Transparent signals. Actionable evidence.
          </p>
        </section>
      </main>
    </div>
  );
}
