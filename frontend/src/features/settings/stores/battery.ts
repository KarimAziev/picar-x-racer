import axios from "axios";
import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";
import { makeUrl } from "@/util/url";

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
        const port = +(import.meta.env.VITE_WS_APP_PORT || "8001");
        const url = makeUrl("/px/api/battery-status", port);
        const response = await axios.get<BatteryResponse>(url);
        const { voltage, percentage } = response.data;
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
