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
import { ensurePrefix } from "@/util/str";
import { MethodsWithOneStringParam, PropertiesOfType } from "@/util/ts-helpers";
import {
  OverlayLinesParams,
  KeypointsParams,
} from "@/features/detection/interface";
import { cloneDeep } from "@/util/obj";

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
  keypointsColor: undefined,
  skeletonColor: undefined,
  bboxesColor: undefined,
  dark: isDarkMode(),
  lines: {
    head: { size: 25, renderFiber: false },
    torso: { size: 60, renderFiber: false },
    arms: { size: 60, renderFiber: false },
    legs: { size: 60, renderFiber: false },
  },
  keypoints: {
    ear: { size: 1 },
    eye: { size: 10 },
    nose: { size: 1 },
    shoulder: { size: 25 },
    elbow: { size: 25 },
    wrist: { size: 25 },
    hip: { size: 25 },
    knee: { size: 25 },
    ankle: { size: 25 },
  },
  keypointsSize: 25,
  skeletonFiber: false,
};
export type ColorPalette = {
  50: string;
  100: string;
  200: string;
  300: string;
  400: string;
  500: string;
  600: string;
  700: string;
  800: string;
  900: string;
  950: string;
};
export interface State {
  primaryColor: string;
  surfaceColor: string;
  dark: boolean;
  skeletonColor?: string;
  keypointsColor?: string;
  bboxesColor?: string;
  lines: OverlayLinesParams;
  keypoints: KeypointsParams;
  keypointsSize: number;
  skeletonFiber: boolean;
}

export const useStore = defineStore("theme", {
  state: () =>
    useLocalStorage<State>("pinia/theme-settings", cloneDeep(defaultState)),
  actions: {
    toggleDarkTheme() {
      const root = document.getElementsByTagName("html")[0];
      root.classList.toggle("p-dark");
      this.dark = isDarkMode();
    },
    updatePrimaryColor(newColor: string) {
      const newPalette = palette(ensurePrefix("#", newColor));
      this.primaryColor = newColor;
      updatePrimaryPalette(newPalette);

      window.dispatchEvent(
        new CustomEvent("update-primary-palette", {
          bubbles: true,
        }),
      );
    },
    updateSurfaceColor(newColor: string) {
      const [name, newPalette] = Object.entries(surfaces).find(
        ([presetName, presetPalette]) =>
          newColor === presetName || newColor === presetPalette[500],
      ) || [newColor, palette(ensurePrefix("#", newColor))];

      updateSurfacePalette(newPalette);
      this.surfaceColor = name;
    },
    updateSkeletonColor(newColor: string) {
      this.skeletonColor = ensurePrefix("#", newColor);
      if (!this.lines) {
        this.lines = cloneDeep(defaultState.lines);
      }
      this.updateBodyColor(this.skeletonColor);
      this.updateHeadlineColor(this.skeletonColor);
      this.updateArmsColor(this.skeletonColor);
      this.updateLegsColor(this.skeletonColor);
    },
    updateSkeletonSize(newSize: number) {
      if (!this.lines) {
        this.lines = cloneDeep(defaultState.lines);
      }
      this.updateBodySize(newSize);
      this.updateHeadlineSize(newSize);
      this.updateArmsSize(newSize);
      this.updateLegsSize(newSize);
    },
    updateBodyColor(newColor: string) {
      this.lines.torso.color = newColor;
    },
    updateHeadlineColor(newColor: string) {
      this.lines.head.color = newColor;
    },
    updateArmsColor(newColor: string) {
      this.lines.arms.color = newColor;
    },
    updateLegsColor(newColor: string) {
      this.lines.legs.color = newColor;
    },
    updateBodySize(newSize: number) {
      this.lines.torso.size = newSize;
    },
    updateHeadlineSize(newSize: number) {
      this.lines.head.size = newSize;
    },
    updateArmsSize(newSize: number) {
      this.lines.arms.size = newSize;
    },
    updateLegsSize(newSize: number) {
      this.lines.legs.size = newSize;
    },

    updateKeypointsColor(newColor: string) {
      this.keypointsColor = newColor;
      Object.keys(this.keypoints).forEach((group) => {
        this.keypoints[group as keyof KeypointsParams].color = newColor;
      });
    },
    updateKeypointsSize(newSize: number) {
      this.keypointsSize = newSize;
      Object.keys(this.keypoints).forEach((group) => {
        this.keypoints[group as keyof KeypointsParams].size = newSize;
      });
    },
    updateBBoxesColor(newColor: string) {
      this.bboxesColor = ensurePrefix("#", newColor);
    },
    init() {
      if (this.dark !== defaultState.dark) {
        this.toggleDarkTheme();
      }

      if (this.primaryColor !== defaultState.primaryColor) {
        this.updatePrimaryColor(this.primaryColor);
      }

      if (
        this.keypointsColor &&
        this.keypointsColor !== defaultState.keypointsColor
      ) {
        this.updateKeypointsColor(this.keypointsColor);
      }

      if (this.bboxesColor && this.bboxesColor !== defaultState.bboxesColor) {
        this.bboxesColor = this.bboxesColor;
      }

      if (
        this.skeletonColor &&
        this.skeletonColor !== defaultState.skeletonColor
      ) {
        this.updateSkeletonColor(this.skeletonColor);
      }

      if (!this.lines) {
        this.lines = cloneDeep(defaultState.lines);
      }
      if (!this.keypoints) {
        this.keypoints = cloneDeep(defaultState.keypoints);
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

export type ThemeState = Omit<
  ReturnType<typeof useStore>,
  keyof ReturnType<typeof defineStore>
>;

export type UpdateColorMethods = MethodsWithOneStringParam<ThemeState>;

export type ThemeProps = PropertiesOfType<Required<ThemeState>, string>;
