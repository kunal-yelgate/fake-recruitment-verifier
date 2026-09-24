import React from "react";
import {
  ShieldCheck,
  Sun,
  Moon,
  History,
  Activity,
  BookOpen,
} from "lucide-react";
import { Button } from "../ui/Button";
import { API_BASE_URL } from "../../services/api";

export function Navbar({
  isDark,
  onToggleTheme,
  onOpenHistory,
  historyCount = 0,
  isBackendConnected = true,
  isMockMode = false,
}) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#d1cdc7]/70 bg-[#f3f0ee]/90 backdrop-blur-xl transition-colors dark:border-white/10 dark:bg-[#141413]/90">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-3">
          <div className="relative rounded-full bg-[#141413] p-2 text-[#f3f0ee] shadow-[0_4px_24px_rgba(20,20,19,0.12)] dark:bg-[#f3f0ee] dark:text-[#141413]">
            <ShieldCheck className="w-5 h-5 text-white" />
            <div className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-[#f3f0ee] bg-[#f37338] dark:border-[#141413] animate-pulse" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-medium tracking-tight text-[#141413] dark:text-[#f3f0ee] sm:text-lg">
                TrueRecruit
              </span>
              <span className="hidden rounded-full border border-[#cf4500]/25 bg-[#cf4500]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#cf4500] dark:text-[#f37338] sm:inline-block">
                OSINT Radar
              </span>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Engine Status Indicator */}
          <div className="hidden items-center gap-1.5 rounded-full border border-[#d1cdc7] bg-white/50 px-3 py-1.5 text-xs font-medium text-[#696969] dark:border-white/10 dark:bg-white/5 dark:text-[#d1cdc7] lg:flex">
            <Activity className="w-3.5 h-3.5 text-emerald-500 animate-pulse" />
            <span>
              {isMockMode
                ? "Demo mode"
                : isBackendConnected
                  ? "Engine ready"
                  : "Engine offline"}
            </span>
          </div>

          {/* History Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenHistory}
            className="relative"
            title="Scan History"
          >
            <History className="w-4 h-4 text-slate-600 dark:text-slate-400" />
            <span className="hidden sm:inline">History</span>
            {historyCount > 0 && (
              <span className="ml-1 rounded-full bg-[#cf4500] px-1.5 py-0.2 text-[10px] font-bold text-white">
                {historyCount}
              </span>
            )}
          </Button>

          {/* Swagger API Docs */}
          {API_BASE_URL && (
            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="hidden items-center gap-1 rounded-full border border-[#d1cdc7] px-3 py-1.5 text-xs font-medium text-[#696969] transition-colors hover:bg-white hover:text-[#141413] dark:border-white/10 dark:text-[#d1cdc7] dark:hover:bg-white/10 dark:hover:text-white sm:inline-flex"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>API Docs</span>
            </a>
          )}

          {/* Theme Toggle Button */}
          <button
            type="button"
            onClick={onToggleTheme}
            className="cursor-pointer rounded-full border border-[#141413] bg-transparent p-2 text-[#141413] transition-colors hover:bg-white dark:border-[#f3f0ee] dark:text-[#f3f0ee] dark:hover:bg-white/10"
            aria-label="Toggle theme"
          >
            {isDark ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-slate-700" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
