import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--panel)",
        "panel-glass": "var(--panel-glass)",
        "panel-border": "var(--panel-border)",
        text: "var(--text)",
        muted: "var(--muted)",
        accent: "var(--accent)",
        "accent-glow": "var(--accent-glow)",
        danger: "var(--danger)",
        warning: "var(--warning)",
        success: "var(--success)"
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.05), inset 0 0 0 1px var(--panel-border)",
        "glass-hover": "0 14px 45px 0 rgba(0, 0, 0, 0.08), inset 0 0 0 1px var(--panel-border), 0 0 20px 0 var(--accent-glow)",
        floating: "0 20px 40px -10px rgba(0,0,0,0.1), 0 0 0 1px var(--panel-border)",
        "inner-glow": "inset 0 1px 1px 0 rgba(255,255,255,0.1)"
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'hero-glow': 'conic-gradient(from 180deg at 50% 50%, var(--accent-glow) 0deg, transparent 180deg, var(--accent-glow) 360deg)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        }
      }
    }
  },
  plugins: []
};

export default config;
