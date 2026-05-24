import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#000000",
        ink: "#fcfdff",
        body: "rgba(252,253,255,0.86)",
        charcoal: "rgba(252,253,255,0.7)",
        mute: "#a1a4a5",
        ash: "#888e90",
        stone: "#464a4d",
        primary: "#fcfdff",
        "primary-on": "#000000",
        "surface-card": "#0a0a0c",
        "surface-elevated": "#101012",
        "surface-deep": "#06060a",
        hairline: "rgba(255,255,255,0.06)",
        "hairline-strong": "rgba(255,255,255,0.14)",
        "divider-soft": "rgba(255,255,255,0.04)",
        "accent-orange": "#ff801f",
        "accent-blue": "#3b9eff",
        "accent-green": "#11ff99",
        "accent-red": "#ff2047",
        "accent-yellow": "#ffc53d",
      },
      borderRadius: {
        md: "8px",
        lg: "12px",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Georgia", "Times New Roman", "serif"],
        mono: ["Geist Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      maxWidth: {
        content: "1200px",
      },
    },
  },
  plugins: [],
} satisfies Config;

