import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager";
import type { Nullable } from "@/util/ts-helpers";
import { makeUrl } from "@/util/url";
import { JSONSchema } from "@/features/controller/interface";
import { Battery } from "@/features/settings/interface";

export interface Field {
  type: string | string[];
  label: string;
  description: string;
  options?: (string | number)[];
}
export interface CalibrationMode {
  type: string;
  label: string;
  description: string;
  examples: string[];
  options?: string[];
}
export interface Servo {
  servo_pin: Pin;
  min_angle: CalibrationOffset;
  max_angle: CalibrationOffset;
  calibration_offset: CalibrationOffset;
  calibration_mode: CalibrationMode;
  name: CalibrationMode;
}

export interface CalibrationOffset {
  type: CalibrationOffsetType;
  label: string;
  description: string;
  examples: number[];
  options?: number[];
}

export enum CalibrationOffsetType {
  Float = "float",
  Int = "int",
  Literal = "literal",
}

export interface Pin {
  type: TypeElement[];
  label: string;
  description: string;
  examples: Array<number | string>;
}

export enum TypeElement {
  Int = "int",
  Str = "str",
}

export interface TMotor {
  dir_pin: Pin;
  pwm_pin: Pin;
  max_speed: CalibrationOffset;
  name: CalibrationMode;
  calibration_direction: CalibrationOffset;
  calibration_speed_offset: CalibrationOffset;
  period: CalibrationOffset;
  prescaler: CalibrationOffset;
}

export interface FieldsConfig {
  cam_pan_servo: Servo;
  cam_tilt_servo: Servo;
  steering_servo: Servo;
  left_motor: TMotor;
  right_motor: TMotor;
}

export interface State {
  data: Data;
  loading: boolean;
  config: JSONSchema | null;
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
  name: null,
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
      const port = +(import.meta.env.VITE_WS_APP_PORT || "8001");
      const url = makeUrl("px/api/settings/robot-fields", port);
      try {
        this.loading = true;
        const response = await axios.get<JSONSchema>(url);

        this.config = response.data;
      } catch (error) {
        messager.handleError(error);
      } finally {
        this.loading = false;
      }
    },
    async fetchData() {
      const messager = useMessagerStore();
      const port = +(import.meta.env.VITE_WS_APP_PORT || "8001");
      const url = makeUrl("px/api/settings/config", port);
      try {
        this.loading = true;
        const response = await axios.get<Data>(url);

        this.data = response.data;
      } catch (error) {
        messager.handleError(error, `Error fetching robot config`);
      } finally {
        this.loading = false;
      }
    },
  },
});
