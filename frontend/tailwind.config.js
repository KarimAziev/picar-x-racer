const config = {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  darkMode: ["selector", '[class="p-dark"]'],
  theme: {
    extend: {
      fontFamily: {
        "tt-octosquares": ["var(--font-family)", "sans-serif"],
      },
      colors: {
        "robo-color-primary": "var(--robo-color-primary)",
        error: "var(--color-error)",
        "button-text-primary-hover-background":
          "var(--p-button-text-primary-hover-background)",
      },
      boxShadow: {
        primary: "0px 0px 4px 2px var(--robo-color-primary)",
      },
      zIndex: {
        11: "11",
        12: "12",
      },
    },
  },
};

export default config;
