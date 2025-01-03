import { defineStore } from "pinia";

export interface State {
  fps: number | null;
  loading?: boolean;
}

export const useStore = defineStore("fps", {
  state: (): State => ({ fps: null }),
  actions: {
    updateFPS(fps: number | null) {
      if (Math.abs((this.fps || 0) - (fps || 0)) > 0.1) {
        this.fps = fps;
      }
    },
  },
});
