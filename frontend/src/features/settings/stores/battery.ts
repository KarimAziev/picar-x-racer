import { defineStore } from "pinia";
import { retrieveError } from "@/util/error";
import { robotApi } from "@/api";

export interface BatteryResponse {
  name: string;
  voltage: number | null;
  current: number | null;
  percentage: number | null;
  error: string | null;
}

export interface State {
  batteries: BatteryResponse[];
  loading: boolean;
  error?: string;
}

const defaultState: State = {
  loading: true,
  batteries: [],
};

export const useStore = defineStore("battery", {
  state: (): State => ({ ...defaultState, batteries: [] }),

  actions: {
    mergeBatteryMetrics(payload: BatteryResponse[]) {
      payload.forEach((metrics) => {
        const index = this.batteries.findIndex(
          (battery) => battery.name === metrics.name,
        );
        if (index === -1) {
          this.batteries.push(metrics);
        } else {
          this.batteries[index] = metrics;
        }
      });
      this.loading = false;
      this.error = undefined;
    },
    async fetchBatteryMetrics() {
      try {
        this.loading = true;
        const response = await robotApi.get<BatteryResponse[]>(
          "/px/api/battery-status",
        );
        this.batteries = response;
        this.error = undefined;
      } catch (error) {
        this.error = retrieveError(error).text;
      } finally {
        this.loading = false;
      }
    },
  },
});
