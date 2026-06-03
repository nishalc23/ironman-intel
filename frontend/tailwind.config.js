/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ironman: {
          red: "#E8001C",
          dark: "#080810",
          card: "#0E0E1A",
          border: "#1A1A28",
          muted: "#6B7280",
        },
      },
    },
  },
  plugins: [],
};
