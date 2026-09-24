import React from "react";
import { ShieldCheck } from "lucide-react";

export function Footer() {
  return (
    <footer className="mt-12 border-t border-[#d1cdc7]/70 py-6 text-xs text-[#696969] transition-colors dark:border-white/10 dark:text-[#d1cdc7]">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <span className="inline-flex items-center gap-2 font-medium text-[#141413] dark:text-[#f3f0ee]">
          <ShieldCheck className="h-4 w-4 text-[#cf4500] dark:text-[#f37338]" />
          TrueRecruit
        </span>
        <span>Private by design. Evidence before action.</span>
      </div>
    </footer>
  );
}
