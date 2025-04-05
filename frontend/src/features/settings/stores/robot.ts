import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager";
import type { Nullable } from "@/util/ts-helpers";

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
  config: Partial<FieldsConfig>;
}

type ServoCalibrationMode = "sum" | "negative";

export interface ServoConfig {
  servo_pin: Nullable<string | number>;
  min_angle: number;
  max_angle: number;
  calibration_offset: Nullable<number>;
  calibration_mode?: Nullable<ServoCalibrationMode>;
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
}

const defaultServo = {
  servo_pin: null,
  min_angle: -30,
  max_angle: 30,
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
  config: {},
  data: {
    cam_pan_servo: defaultServo,
    cam_tilt_servo: defaultServo,
    steering_servo: defaultServo,
    left_motor: motorDefaults,
    right_motor: motorDefaults,
    led: ledDefaults,
  },
};

export const useStore = defineStore("robot", {
  state: () => ({ ...defaultState }),

  getters: {
    maxSpeed({ data }) {
      return Math.min(
        data.left_motor.max_speed || 100,
        data.right_motor.max_speed || 100,
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
        steering_servo_offset: steering_servo.calibration_offset,
        cam_pan_servo_offset: cam_pan_servo.calibration_offset,
        cam_tilt_servo_offset: cam_tilt_servo.calibration_offset,
        left_motor_direction: left_motor.calibration_direction,
        right_motor_direction: right_motor.calibration_direction,
      };
    },
  },
  actions: {
    async fetchFieldsConfig() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const baseURL =
          import.meta.env.VITE_CONTROL_APP_URL || "http://127.0.0.1:8001";
        const response = await axios.get<FieldsConfig>(
          `${baseURL}/px/api/settings/robot-fields`,
        );
        this.config = response.data;
      } catch (error) {
        messager.handleError(error);
      } finally {
        this.loading = false;
      }
    },
    async fetchData() {
      const messager = useMessagerStore();
      try {
        const baseURL =
          import.meta.env.VITE_CONTROL_APP_URL || "http://127.0.0.1:8001";
        this.loading = true;
        const response = await axios.get<Data>(
          `${baseURL}/px/api/settings/config`,
        );
        this.data = response.data;
      } catch (error) {
        messager.handleError(error, `Error fetching robot config`);
      } finally {
        this.loading = false;
      }
    },
  },
});
