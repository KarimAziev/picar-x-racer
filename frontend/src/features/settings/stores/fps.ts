import { defineStore } from "pinia";
import { roundToOneDecimalPlace } from "@/util/number";

export interface State {
  fps: number | null;
  serverFPS: number | null;
  loading?: boolean;
}

export const useStore = defineStore("fps", {
  state: (): State => ({ fps: null, serverFPS: null }),
  actions: {
    updateFPS(fps: number | null) {
      if (
        (Number.isInteger(fps) && !Number.isInteger(this.serverFPS)) ||
        Math.abs((this.serverFPS || 0) - (fps || 0)) > 0.1
      ) {
        this.fps = roundToOneDecimalPlace(fps || 0);
      }
    },
    updateServerFPS(fps: number | null) {
      if (
        (Number.isInteger(fps) && !Number.isInteger(this.serverFPS)) ||
        Math.abs((this.serverFPS || 0) - (fps || 0)) > 0.1
      ) {
        this.serverFPS = fps;
      }
    },
  },
});
