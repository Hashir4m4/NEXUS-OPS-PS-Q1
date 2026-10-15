/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        nexus: {
          void: "#04060B",
          black: "#060913",
          navy: "#0A0F1F",
          card: "rgba(13, 20, 38, 0.75)",
          cardHover: "rgba(20, 32, 58, 0.85)",
          surface: "rgba(18, 28, 52, 0.5)",
          border: "rgba(0, 240, 255, 0.18)",
          borderGlow: "rgba(0, 240, 255, 0.5)",
          borderSubtle: "rgba(255, 255, 255, 0.08)",
          cyan: "#00F0FF",
          blue: "#3B82F6",
          violet: "#8B5CF6",
          purple: "#A855F7",
          magenta: "#EC4899",
          emerald: "#10B981",
          amber: "#F59E0B",
          rose: "#F43F5E",
          muted: "#94A3B8",
          dim: "#64748B",
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'glow-cyan': '0 0 25px -4px rgba(0, 240, 255, 0.35)',
        'glow-cyan-sm': '0 0 12px -2px rgba(0, 240, 255, 0.4)',
        'glow-blue': '0 0 25px -4px rgba(59, 130, 246, 0.35)',
        'glow-violet': '0 0 25px -4px rgba(139, 92, 246, 0.35)',
        'glow-emerald': '0 0 20px -4px rgba(16, 185, 129, 0.35)',
        'glow-amber': '0 0 20px -4px rgba(245, 158, 11, 0.35)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.5)',
        'hud': 'inset 0 0 20px rgba(0, 240, 255, 0.04), 0 8px 32px 0 rgba(0, 0, 0, 0.6)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'grid-pattern': 'linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px)',
        'cyber-grid': 'linear-gradient(to right, rgba(0, 240, 255, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 240, 255, 0.05) 1px, transparent 1px)',
      },
      keyframes: {
        pulseSlow: {
          '0%, 100%': { opacity: 0.9, transform: 'scale(1)' },
          '50%': { opacity: 0.6, transform: 'scale(0.98)' },
        },
        pulseGlow: {
          '0%, 100%': { filter: 'drop-shadow(0 0 8px rgba(0, 240, 255, 0.6))' },
          '50%': { filter: 'drop-shadow(0 0 2px rgba(0, 240, 255, 0.2))' },
        },
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(1000%)' },
        }
      },
      animation: {
        'pulse-slow': 'pulseSlow 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
        'scanline': 'scanline 8s linear infinite',
      }
    },
  },
  plugins: [],
};
