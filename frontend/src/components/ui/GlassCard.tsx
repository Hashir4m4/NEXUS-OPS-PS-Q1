import React from "react";
import { cn } from "../../lib/utils";

interface GlassCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  variant?: "default" | "elevated" | "hud" | "interactive";
  glowColor?: "cyan" | "blue" | "violet" | "magenta" | "emerald" | "amber" | "none";
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  badge?: React.ReactNode;
  action?: React.ReactNode;
  showBrackets?: boolean;
  children: React.ReactNode;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  variant = "default",
  glowColor = "none",
  title,
  subtitle,
  badge,
  action,
  showBrackets = false,
  className,
  children,
  ...props
}) => {
  const variantStyles = {
    default: "bg-nexus-card border border-nexus-border/60 backdrop-blur-xl",
    elevated: "bg-nexus-cardHover border border-nexus-borderGlow/40 backdrop-blur-2xl shadow-glass",
    hud: "bg-nexus-navy/80 border border-nexus-cyan/25 backdrop-blur-xl shadow-hud",
    interactive: "bg-nexus-card border border-nexus-border/60 hover:border-nexus-cyan/60 hover:bg-nexus-cardHover transition-all duration-300 cursor-pointer",
  };

  const glowStyles = {
    cyan: "shadow-glow-cyan border-nexus-cyan/40",
    blue: "shadow-glow-blue border-nexus-blue/40",
    violet: "shadow-glow-violet border-nexus-violet/40",
    magenta: "shadow-[0_0_25px_-4px_rgba(236,72,153,0.35)] border-nexus-magenta/40",
    emerald: "shadow-glow-emerald border-nexus-emerald/40",
    amber: "shadow-glow-amber border-nexus-amber/40",
    none: "",
  };

  return (
    <div
      className={cn(
        "relative rounded-xl p-5 text-slate-100 overflow-hidden",
        variantStyles[variant],
        glowStyles[glowColor],
        showBrackets && "hud-bracket",
        className
      )}
      {...props}
    >
      {/* Subtle top specular highlight */}
      <div className="absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent pointer-events-none" />

      {/* Header if title, subtitle, or action provided */}
      {(title || subtitle || action || badge) && (
        <div className="flex items-start justify-between gap-4 mb-4 pb-3 border-b border-white/[0.06]">
          <div>
            <div className="flex items-center gap-2">
              {title && (
                <h3 className="font-semibold text-sm tracking-wide text-white flex items-center gap-2">
                  {title}
                </h3>
              )}
              {badge}
            </div>
            {subtitle && (
              <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                {subtitle}
              </p>
            )}
          </div>
          {action && <div className="flex items-center gap-2 shrink-0">{action}</div>}
        </div>
      )}

      {children}
    </div>
  );
};
