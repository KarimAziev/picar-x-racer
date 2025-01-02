/** @type {import('tailwindcss').Config} */
// @ts-ignore
import primeui from "tailwindcss-primeui"; // @ts-ignore

export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  darkMode: ["selector", '[class="p-dark"]'],
  plugins: [primeui],
  theme: {
    extend: {
      fontFamily: {
        "tt-octosquares": ["var(--font-family)", "sans-serif"],
      },
      colors: {
        "--robo-color-primary": "var(--robo-color-primary)",
      },
      boxShadow: {
        primary: "0px 0px 4px 2px var(--robo-color-primary)",
      },
    },
  },
};
