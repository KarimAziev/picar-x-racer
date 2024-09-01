import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager/store";

export interface Data {
  [key: string]: string | number;
}
export interface State {
  data: Data;
  loading: boolean;
}

const defaultState: State = {
  loading: false,
  data: {},
};

export const useStore = defineStore("calibration", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get("/api/calibration");
        Object.entries(response.data).forEach(([key, value]) => [
          messager.info(`${value}`, key),
        ]);
        this.data = response.data;
      } catch (error) {
        messager.handleError(error, `Error fetching calibration settings`);
      } finally {
        this.loading = false;
      }
    },
  },
});
