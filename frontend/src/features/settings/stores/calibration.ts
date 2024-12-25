import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager";
import type { Nullable } from "@/util/ts-helpers";

export interface Data {
  steering_servo_offset: Nullable<number>;
  cam_pan_servo_offset: Nullable<number>;
  cam_tilt_servo_offset: Nullable<number>;
  left_motor_direction: Nullable<number>;
  right_motor_direction: Nullable<number>;
}
export interface State {
  data: Data;
  loading: boolean;
}

const defaultState: State = {
  loading: false,
  data: {
    steering_servo_offset: null,
    cam_pan_servo_offset: null,
    cam_tilt_servo_offset: null,
    left_motor_direction: null,
    right_motor_direction: null,
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
          this.data[key as keyof Data] = value;
        });
      } catch (error) {
        messager.handleError(error, `Error fetching calibration settings`);
      } finally {
        this.loading = false;
      }
    },
  },
});
