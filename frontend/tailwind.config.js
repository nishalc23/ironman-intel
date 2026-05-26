/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ironman: {
          red: "#E8001C",
          dark: "#0D0D0D",
          card: "#1A1A1A",
          border: "#2A2A2A",
          muted: "#6B7280",
        },
      },
    },
  },
  plugins: [],
};
