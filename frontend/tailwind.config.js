/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Glassmorphism palette from the ui-ux-pro-max design system.
        ink:     { DEFAULT: "#0F172A", deep: "#080D1A", surface: "#1B2336" },
        paper:   { DEFAULT: "#F8FAFC", muted: "#94A3B8", dim: "#64748B" },
        accent:  { DEFAULT: "#22C55E", ink: "#0F172A" },
        edge:    "#475569",
        danger:  "#EF4444",
        swim:    "#22D3EE",
        bike:    "#F59E0B",
        run:     "#34D399",
        brick:   "#A78BFA",
        rest:    "#8B94A7",
        // Kept so existing references keep compiling while the migration lands.
        ironman: { red: "#EF4444", dark: "#080D1A", card: "#1B2336", border: "#475569", muted: "#94A3B8" },
      },
      fontFamily: {
        sans: ["Fira Sans", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["Fira Code", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
