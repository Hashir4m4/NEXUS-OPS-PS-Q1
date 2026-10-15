import React from "react";
import { cn } from "../../lib/utils";

interface NeonButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "violet" | "outline" | "ghost" | "danger";
  size?: "xs" | "sm" | "md" | "lg";
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  loading?: boolean;
}

export const NeonButton: React.FC<NeonButtonProps> = ({
  variant = "primary",
  size = "md",
  icon,
  iconPosition = "left",
  loading = false,
  className,
  children,
  disabled,
  ...props
}) => {
  const baseStyles =
    "relative inline-flex items-center justify-center font-medium tracking-wide rounded-lg transition-all duration-200 select-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-nexus-cyan/40 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none active:scale-[0.98]";

  const variantStyles = {
    primary:
      "bg-gradient-to-r from-nexus-cyan/90 to-cyan-400 text-nexus-black font-semibold shadow-glow-cyan hover:shadow-[0_0_30px_0_rgba(0,240,255,0.6)] hover:brightness-110",
    secondary:
      "bg-nexus-blue/20 text-nexus-cyan border border-nexus-cyan/40 hover:bg-nexus-cyan/20 hover:border-nexus-cyan shadow-glow-cyan-sm",
    violet:
      "bg-nexus-violet/20 text-violet-300 border border-nexus-violet/40 hover:bg-nexus-violet/30 hover:border-nexus-violet shadow-glow-violet",
    outline:
      "bg-transparent text-slate-200 border border-white/20 hover:border-nexus-cyan/60 hover:text-nexus-cyan hover:bg-nexus-cyan/5",
    ghost:
      "bg-transparent text-slate-400 hover:text-white hover:bg-white/[0.06]",
    danger:
      "bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30 hover:border-rose-400 shadow-[0_0_15px_-3px_rgba(244,63,94,0.4)]",
  };

  const sizeStyles = {
    xs: "text-xs px-2.5 py-1 gap-1.5 h-7",
    sm: "text-xs px-3 py-1.5 gap-2 h-8",
    md: "text-sm px-4 py-2 gap-2 h-10",
    lg: "text-base px-6 py-2.5 gap-2.5 h-12",
  };

  return (
    <button
      className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        icon && iconPosition === "left" && <span className="shrink-0">{icon}</span>
      )}
      <span>{children}</span>
      {!loading && icon && iconPosition === "right" && (
        <span className="shrink-0">{icon}</span>
      )}
    </button>
  );
};
