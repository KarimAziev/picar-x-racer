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
        error: "var(--color-error)",
        "button-text-primary-hover-background":
          "var(--p-button-text-primary-hover-background)",
      },
      boxShadow: {
        primary: "0px 0px 4px 2px var(--robo-color-primary)",
      },
      zIndex: {
        "11": "11",
        "12": "12",
      },
    },
  },
};
