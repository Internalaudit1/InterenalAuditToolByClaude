import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#1b1a17",
        mist: "#f6f2e8",
        ember: "#c25b2c",
        sage: "#53624f",
        sand: "#e9dcc6",
        slate: "#57616e",
        cream: "#fffdf8"
      },
      boxShadow: {
        panel: "0 24px 60px rgba(27, 26, 23, 0.12)"
      },
      backgroundImage: {
        mesh: "radial-gradient(circle at top left, rgba(194,91,44,0.18), transparent 32%), radial-gradient(circle at 85% 10%, rgba(83,98,79,0.16), transparent 26%), linear-gradient(180deg, #fffdf8 0%, #f7f0e3 100%)"
      },
      fontFamily: {
        sans: ["var(--font-manrope)", "sans-serif"],
        serif: ["var(--font-plex-serif)", "serif"]
      }
    }
  },
  plugins: []
};

export default config;

