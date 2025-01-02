/** @type {import('tailwindcss').Config} */
// @ts-ignore
import primeui from "tailwindcss-primeui"; // @ts-ignore

export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  darkMode: ["selector", '[class="p-dark"]'],
  plugins: [primeui],
};
