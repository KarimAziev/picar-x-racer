import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";
import { robotApi } from "@/api";

export interface BatteryResponse {
  voltage: number;
  percentage: number;
}

export interface State extends BatteryResponse {
  loading: boolean;
  error?: string;
}

const defaultState: State = {
  loading: true,
  voltage: 0,
  percentage: 0,
};

export const useStore = defineStore("battery", {
  state: () => ({ ...defaultState }),

  actions: {
    async fetchBatteryStatus() {
      try {
        this.loading = true;
        const response = await robotApi.get<BatteryResponse>(
          "/px/api/battery-status",
        );
        const { voltage, percentage } = response;
        this.voltage = voltage;
        this.percentage = percentage;
        this.error = undefined;
      } catch (error) {
        this.error = retrieveError(error).text;
      } finally {
        this.loading = false;
      }
    },
  },
});
