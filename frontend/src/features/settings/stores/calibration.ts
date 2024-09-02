import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager/store";

export interface Data {
  [key: string]: string | number | null;
}
export interface State {
  data: Data;
  loading: boolean;
}

const defaultState: State = {
  loading: false,
  data: {
    picarx_cam_pan_servo: null,
    picarx_cam_tilt_servo: null,
    picarx_dir_motor: null,
    picarx_dir_servo: null,
  },
};

export const useStore = defineStore("calibration", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get("/api/calibration");
        Object.entries(response.data).forEach(([key, value]) => {
          messager.info(`${value}`, key);
        });
        this.data = { ...this.data, ...response.data };
      } catch (error) {
        messager.handleError(error, `Error fetching calibration settings`);
      } finally {
        this.loading = false;
      }
    },
  },
});
