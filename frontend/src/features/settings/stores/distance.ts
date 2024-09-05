import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";
import axios from "axios";
import { isNumber } from "@/util/guards";

export interface State {
  loading?: boolean;
  error?: string;
  distance: number;
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
        const response = await axios.get("/api/get-distance");
        const distance = response.data.distance;
        this.distance = isNumber(distance) ? distance : 0;
        this.error = undefined;
      } catch (error) {
        console.error("Error distance:", error);
        this.error = retrieveError(error).text;
      } finally {
        this.loading = false;
      }
    },
  },
});
