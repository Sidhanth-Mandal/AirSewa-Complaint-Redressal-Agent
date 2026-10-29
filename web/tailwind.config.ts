import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#0b3d91", 50: "#eef3fb", 100: "#d9e5f7", 600: "#0b3d91", 700: "#093075", 800: "#07265c" },
        saffron: { DEFAULT: "#ff9933", 600: "#c2570c", 100: "#fff1e0" },
        india: { DEFAULT: "#138808", 50: "#e9f6e7", 700: "#0d6606" },
      },
      fontFamily: { sans: ["Segoe UI", "Noto Sans", "Noto Sans Devanagari", "system-ui", "sans-serif"] },
      keyframes: { slidein: { "0%": { opacity: "0", transform: "translateY(-12px)" }, "100%": { opacity: "1", transform: "none" } }, pulsering: { "0%,100%": { boxShadow: "0 0 0 0 rgba(220,38,38,.5)" }, "50%": { boxShadow: "0 0 0 8px rgba(220,38,38,0)" } } },
      animation: { slidein: "slidein .35s ease-out", pulsering: "pulsering 1.6s infinite" },
    },
  },
  plugins: [],
};
export default config;
