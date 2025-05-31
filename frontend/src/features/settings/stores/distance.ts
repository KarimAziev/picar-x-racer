import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";
import { isNumber } from "@/util/guards";
import { robotApi } from "@/api";

export interface State {
  loading?: boolean;
  error?: string;
  distance: number;
  speed?: 0;
}

const defaultState: State = {
  distance: 0,
};

export const useStore = defineStore("distance", {
  state: () => ({ ...defaultState }),

  actions: {
    async fetchDistance() {
      try {
        this.loading = true;
        const response = await robotApi.get<{ distance: number }>(
          "/px/api/get-distance",
        );
        const distance = response.distance;

        this.distance = isNumber(distance) ? distance : 0;
        this.error = undefined;
      } catch (error) {
        this.error = retrieveError(error).text;
      } finally {
        this.loading = false;
      }
    },
  },
});
