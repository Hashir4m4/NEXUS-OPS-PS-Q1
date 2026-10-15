import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(val: number, decimals: number = 4): string {
  if (isNaN(val) || val === null || val === undefined) return "—";
  return val.toFixed(decimals);
}

export function formatPercentage(val: number, decimals: number = 1): string {
  if (isNaN(val) || val === null || val === undefined) return "—";
  return `${(val * 100).toFixed(decimals)}%`;
}
