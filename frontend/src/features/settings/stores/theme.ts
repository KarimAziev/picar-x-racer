import { defineStore } from "pinia";
import {
  updatePrimaryPalette,
  palette,
  updateSurfacePalette,
} from "@primevue/themes";
import { useLocalStorage } from "@vueuse/core";
import { defaultPrimaryColor } from "@/presets/RoboPreset";
import { isDarkMode } from "@/util/theme";
import { surfaces } from "@/presets/surfaces";

export const defaultLightState = {
  primaryColor: defaultPrimaryColor,
  surfaceColor: "slate",
};

export const defaultDarkState = {
  primaryColor: defaultPrimaryColor,
  surfaceColor: "robo",
};

export const defaultState = {
  ...defaultDarkState,
  dark: isDarkMode(),
};

export interface State {
  primaryColor: string;
  surfaceColor: string;
  dark: boolean;
}

export const useStore = defineStore("theme", {
  state: () => useLocalStorage<State>("pinia/theme", defaultState),
  actions: {
    toggleDarkTheme() {
      const root = document.getElementsByTagName("html")[0];
      root.classList.toggle("p-dark");
      this.dark = isDarkMode();
    },
    updatePrimaryColor(newColor: string) {
      const newPalette = palette(newColor);
      this.primaryColor = newColor;
      updatePrimaryPalette(newPalette);
      window.dispatchEvent(
        new CustomEvent("update-primary-palette", {
          bubbles: true,
        }),
      );
    },
    updateSurfaceColor(newColor: string) {
      const newPalette =
        surfaces[newColor as keyof typeof surfaces] || palette(newColor);
      updateSurfacePalette(newPalette);
      this.surfaceColor = newColor;
    },
    init() {
      if (this.dark !== defaultState.dark) {
        this.toggleDarkTheme();
      }

      if (this.primaryColor !== defaultState.primaryColor) {
        this.updatePrimaryColor(this.primaryColor);
      }

      if (!this.isSurfaceColorDefault) {
        this.updateSurfaceColor(this.surfaceColor);
      }
    },
    resetTheme() {
      this.resetPrimaryColor();
      this.resetSurface();
    },
    resetSurface() {
      this.updateSurfaceColor(this.defaultState.surfaceColor);
    },
    resetPrimaryColor() {
      this.updatePrimaryColor(defaultState.primaryColor);
    },
  },
  getters: {
    isPrimaryColorDefault({ primaryColor }) {
      return primaryColor === defaultState.primaryColor;
    },
    defaultState({ dark }): {
      primaryColor: string;
      surfaceColor: string;
    } {
      return dark ? defaultDarkState : defaultLightState;
    },
    defaultSurfaceColor({ dark }) {
      return dark
        ? defaultLightState.surfaceColor
        : defaultDarkState.surfaceColor;
    },
    isSurfaceColorDefault({ surfaceColor }): boolean {
      return surfaceColor === this.defaultState.surfaceColor;
    },
  },
});
