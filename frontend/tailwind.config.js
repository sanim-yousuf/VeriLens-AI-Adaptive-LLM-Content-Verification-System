/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202A",
        paper: "#F6F7F4",
        cloud: "#EEF1ED",
        line: "#D9DED7",
        graphite: "#4B5563",
        moss: "#427A5B",
        sky: "#2B6CB0",
        saffron: "#D97706",
        coral: "#C2413A"
      },
      boxShadow: {
        panel: "0 12px 36px rgba(23, 32, 42, 0.08)",
        focus: "0 0 0 4px rgba(43, 108, 176, 0.14)"
      }
    }
  },
  plugins: []
};
