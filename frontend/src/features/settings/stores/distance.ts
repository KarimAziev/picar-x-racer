import axios from "axios";
import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";
import { isNumber } from "@/util/guards";
import { makeUrl } from "@/util/url";

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
        const response = await axios.get(makeUrl("/px/api/get-distance", 8001));
        const distance = response.data.distance;
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
