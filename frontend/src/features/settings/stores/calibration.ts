import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager";
import type { Nullable } from "@/util/ts-helpers";

export interface Data {
  [key: string]: Nullable<string>;
}
export interface State {
  data: Data;
  loading: boolean;
}

const defaultState: State = {
  loading: false,
  data: {
    picarx_dir_servo: null,
    picarx_cam_pan_servo: null,
    picarx_cam_tilt_servo: null,
    picarx_dir_motor: null,
  },
};

export const useStore = defineStore("calibration", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get<Data>("/api/settings/calibration");
        Object.entries(response.data).forEach(([key, value]) => {
          messager.info(`${value}`, key);
          this.data[key] = value;
        });
      } catch (error) {
        messager.handleError(error, `Error fetching calibration settings`);
      } finally {
        this.loading = false;
      }
    },
  },
});
