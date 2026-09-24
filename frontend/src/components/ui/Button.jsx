import React from "react";
import { Loader2 } from "lucide-react";

export function Button({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  disabled = false,
  icon: Icon,
  className = "",
  ...props
}) {
  const baseStyles =
    "inline-flex items-center justify-center rounded-[20px] font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";

  const sizeStyles = {
    sm: "px-3 py-1.5 text-xs gap-1.5",
    md: "px-4 py-2.5 text-sm gap-2",
    lg: "px-6 py-3 text-base gap-2.5",
  };

  const variantStyles = {
    primary:
      "bg-[#141413] hover:bg-[#262627] text-[#f3f0ee] shadow-[0_12px_24px_rgba(20,20,19,0.12)] focus:ring-[#141413] border border-[#141413] active:scale-[0.98] dark:bg-[#f3f0ee] dark:text-[#141413] dark:hover:bg-white dark:border-[#f3f0ee]",
    secondary:
      "bg-white/60 hover:bg-white text-[#141413] border border-[#d1cdc7] focus:ring-[#141413] dark:bg-white/5 dark:text-[#f3f0ee] dark:border-white/10 dark:hover:bg-white/10",
    danger:
      "bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/25 focus:ring-rose-500 border border-transparent active:scale-[0.98]",
    outline:
      "bg-transparent hover:bg-white text-[#555555] dark:hover:bg-white/10 dark:text-[#d1cdc7] border border-[#d1cdc7] dark:border-white/15 focus:ring-[#141413]",
    ghost:
      "bg-transparent hover:bg-slate-100 dark:hover:bg-slate-800/60 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 border-transparent",
  };

  return (
    <button
      disabled={disabled || isLoading}
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-current" />
          <span>{children}</span>
        </>
      ) : (
        <>
          {Icon && <Icon className="w-4 h-4 flex-shrink-0" />}
          <span>{children}</span>
        </>
      )}
    </button>
  );
}
