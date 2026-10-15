import React from "react";
import { cn } from "../../lib/utils";

interface StatusBadgeProps {
  variant?: "cyan" | "emerald" | "magenta" | "violet" | "amber" | "neutral" | "blue";
  size?: "sm" | "md";
  dot?: boolean;
  pulse?: boolean;
  className?: string;
  children: React.ReactNode;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  variant = "cyan",
  size = "sm",
  dot = true,
  pulse = false,
  className,
  children,
}) => {
  const variantStyles = {
    cyan: "bg-cyan-500/10 text-nexus-cyan border-cyan-500/30",
    emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    magenta: "bg-pink-500/10 text-pink-400 border-pink-500/30",
    violet: "bg-violet-500/10 text-violet-400 border-violet-500/30",
    amber: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    blue: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    neutral: "bg-slate-800/60 text-slate-400 border-slate-700/60",
  };

  const dotColors = {
    cyan: "bg-nexus-cyan shadow-[0_0_8px_#00F0FF]",
    emerald: "bg-emerald-400 shadow-[0_0_8px_#10B981]",
    magenta: "bg-pink-400 shadow-[0_0_8px_#EC4899]",
    violet: "bg-violet-400 shadow-[0_0_8px_#8B5CF6]",
    amber: "bg-amber-400 shadow-[0_0_8px_#F59E0B]",
    blue: "bg-blue-400 shadow-[0_0_8px_#3B82F6]",
    neutral: "bg-slate-400",
  };

  const sizeStyles = {
    sm: "text-[11px] px-2 py-0.5 gap-1.5",
    md: "text-xs px-2.5 py-1 gap-2",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center font-mono font-medium rounded-full border tracking-wide uppercase",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            "w-1.5 h-1.5 rounded-full shrink-0",
            dotColors[variant],
            pulse && "animate-pulse"
          )}
        />
      )}
      <span>{children}</span>
    </span>
  );
};
