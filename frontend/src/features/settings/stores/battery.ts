import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";
import axios from "axios";

export interface State {
  loading?: boolean;
  error?: string;
  voltage: number;
}

const defaultState: State = {
  voltage: 0,
};

export const useStore = defineStore("battery", {
  state: () => ({ ...defaultState }),

  actions: {
    async fetchBatteryStatus() {
      try {
        this.loading = true;
        const response = await axios.get("/api/battery-status");
        const voltage = response.data.voltage;
        this.voltage = voltage;
        this.error = undefined;
      } catch (error) {
        console.error("Error fetching voltage:", error);
        this.error = retrieveError(error).text;
      } finally {
        this.loading = false;
      }
    },
  },
});
