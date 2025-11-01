import { defineStore } from "pinia";
import { useMessagerStore } from "@/features/messager";
import type { Nullable } from "@/util/ts-helpers";
import { Battery } from "@/features/settings/interface";
import type { JSONSchema } from "@/ui/JsonSchema/interface";
import { robotApi } from "@/api";
import { omit, pick } from "@/util/obj";

export interface State {
  data: Data;
  loading: boolean;
  config: JSONSchema | null;
  partialData?: Partial<Data>;
  loaded?: boolean;
}

type ServoCalibrationMode = "sum" | "negative";

export interface ServoConfig {
  servo_pin: Nullable<string | number>;
  min_angle: number;
  max_angle: number;
  calibration_offset: Nullable<number>;
  calibration_mode?: Nullable<ServoCalibrationMode>;
  dec_step: number;
  inc_step: number;
  name: Nullable<string>;
  reverse: boolean;
  enabled: boolean;
}

export interface MotorConfig {
  dir_pin: Nullable<string | number>;
  pwm_pin: Nullable<string | number>;
  max_speed: Nullable<number>;
  name: Nullable<string>;
  calibration_direction: Nullable<number>;
  calibration_speed_offset: Nullable<number>;
  period: Nullable<number>;
  prescaler: Nullable<number>;
}

export interface ServoData {
  cam_pan_servo: ServoConfig;

  cam_tilt_servo: ServoConfig;
  steering_servo: ServoConfig;
}

export type ServoCalibrationData = {
  [P in keyof ServoData]: Pick<ServoConfig, "calibration_offset">;
};

export interface MotorsData {
  left_motor: MotorConfig;
  right_motor: MotorConfig;
}

export interface CalibrationData
  extends ServoCalibrationData,
    MotorsCalibrationData {}

export type MotorsCalibrationData = {
  [P in keyof MotorsData]: Pick<MotorConfig, "calibration_direction">;
};

export interface LEDConfig {
  interval: number | null;
  pin: number | string | null;
  name: string | null;
}
export interface Data extends ServoData, MotorsData {
  led: LEDConfig;
  battery: Battery;
}

const defaultServo = {
  servo_pin: null,
  min_angle: -30,
  max_angle: 30,
  dec_step: -5,
  inc_step: 5,
  calibration_offset: null,
  calibration_mode: null,
  reverse: false,
  name: null,
  enabled: true,
};

const motorDefaults = {
  dir_pin: null,
  pwm_pin: null,
  max_speed: null,
  name: null,
  calibration_direction: null,
  calibration_speed_offset: null,
  period: null,
  prescaler: null,
};
const ledDefaults = {
  name: null,
  pin: null,
  interval: null,
};
const defaultState: State = {
  loading: false,
  loaded: false,
  config: null,
  data: {
    cam_pan_servo: defaultServo,
    cam_tilt_servo: defaultServo,
    steering_servo: defaultServo,
    left_motor: motorDefaults,
    right_motor: motorDefaults,
    led: ledDefaults,
    battery: {
      full_voltage: 8.4,
      warn_voltage: 7.15,
      danger_voltage: 6.5,
      min_voltage: 6.0,
      auto_measure_seconds: 60,
      cache_seconds: 2,
      enabled: false,
    },
  },
};

export const useStore = defineStore("robot", {
  state: () => ({ ...defaultState }),

  getters: {
    maxSpeed({ data }) {
      return Math.min(
        data?.left_motor?.max_speed || 100,
        data?.right_motor?.max_speed || 100,
      );
    },
    calibration({
      data: {
        steering_servo,
        cam_pan_servo,
        cam_tilt_servo,
        left_motor,
        right_motor,
      },
    }) {
      return {
        steering_servo_offset: steering_servo?.calibration_offset,
        cam_pan_servo_offset: cam_pan_servo?.calibration_offset,
        cam_tilt_servo_offset: cam_tilt_servo?.calibration_offset,
        left_motor_direction: left_motor?.calibration_direction,
        right_motor_direction: right_motor?.calibration_direction,
      };
    },
  },
  actions: {
    async fetchFieldsConfig() {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        const response = await robotApi.get<JSONSchema>(
          "px/api/settings/json-schema",
        );

        this.config = response;
      } catch (error) {
        messager.handleError(error);
      } finally {
        this.loading = false;
      }
    },
    async fetchData() {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        const response = await robotApi.get<Data>("px/api/settings/config");

        this.data = response;
      } catch (error) {
        messager.handleError(error, `Error fetching robot config`);
      } finally {
        this.loading = false;
        this.loaded = true;
      }
    },
    async saveData(data: Data) {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        const response = await robotApi.put<Data>(
          "/px/api/settings/config",
          data,
        );

        this.data = response;
      } catch (error) {
        messager.handleError(error, `Error fetching robot config`);
      } finally {
        this.loading = false;
      }
    },
    async updatePartialData(data: Partial<Data>) {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        await robotApi.patch<Partial<Data>>("px/api/settings/config", data);
      } catch (error) {
        messager.handleError(error, `Error fetching robot config`);
      } finally {
        this.loading = false;
      }
    },
    mergeCalibrationData(payload: Partial<CalibrationData>) {
      const servos = omit(["left_motor", "right_motor"], payload);
      const motors = pick(["left_motor", "right_motor"], payload);
      Object.entries(servos).forEach(([key, cal]) => {
        this.data[key as keyof ServoCalibrationData].calibration_offset =
          cal.calibration_offset;
      });

      Object.entries(motors).forEach(([key, cal]) => {
        this.data[key as keyof MotorsCalibrationData].calibration_direction =
          cal.calibration_direction;
      });
    },
  },
});
