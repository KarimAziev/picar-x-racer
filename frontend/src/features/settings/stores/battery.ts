import axios from "axios";
import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";

export interface BatteryResponse {
  voltage: number;
  percentage: number;
}

export interface State extends BatteryResponse {
  loading?: boolean;
  error?: string;
}

const defaultState: State = {
  voltage: 0,
  percentage: 0,
};

export const useStore = defineStore("battery", {
  state: () => ({ ...defaultState }),

  actions: {
    async fetchBatteryStatus() {
      try {
        this.loading = true;
        const response = await axios.get<BatteryResponse>(
          "/api/battery-status",
        );
        const { voltage, percentage } = response.data;
        this.voltage = voltage;
        this.percentage = percentage;
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
