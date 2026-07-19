import { defineStore } from "pinia";
import { useMessagerStore } from "@/features/messager";
import type { Nullable } from "@/util/ts-helpers";
import { Battery } from "@/features/settings/interface";
import type { JSONSchema } from "@/ui/JsonSchema/interface";
import { robotApi } from "@/api";

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
  enabled: boolean;
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
  motors: MotorConfig[];
}

export interface MotionControlConfig {
  enabled: boolean;
  control_frequency_hz: number;
  command_timeout_ms: number;
  max_forward_speed_mps: number | null;
  max_reverse_speed_mps: number | null;
}

export interface AckermannOdometryConfig {
  enabled: boolean;
  wheelbase_m: number | null;
  wheel_radius_m: number | null;
  encoder_ticks_per_revolution: number | null;
  gear_ratio: number;
  max_steering_age_ms: number;
}

export interface StaticTransformConfig {
  x_m: number;
  y_m: number;
  z_m: number;
  roll_rad: number;
  pitch_rad: number;
  yaw_rad: number;
}

export interface LocalizationSensorsConfig {
  lidar: {
    enabled: boolean;
    driver: "rplidar_c1";
    port: string;
    baudrate: number;
    timeout_s: number;
    frame_id: string;
    transform: StaticTransformConfig;
    range_min_m: number | null;
    range_max_m: number | null;
    angular_resolution_deg: number;
    min_measurements_per_scan: number;
  };
  imu: {
    enabled: boolean;
    driver: "sh3001";
    bus: number;
    address: number | string;
    frame_id: string;
    transform: StaticTransformConfig;
    sample_frequency_hz: number;
    accelerometer_range_g: 2 | 4 | 8 | 16;
    gyroscope_range_dps: 125 | 250 | 500 | 1000 | 2000;
  };
  encoder: {
    enabled: boolean;
    driver: "external";
    frame_id: string;
    sample_frequency_hz: number;
  };
}

export interface LidarSafetyConfig {
  enabled: boolean;
  front_half_angle_deg: number;
  stop_distance_m: number | null;
  slow_distance_m: number | null;
  scan_timeout_ms: number;
  min_obstacle_points: number;
}

export type CalibrationData = Partial<ServoCalibrationData> &
  MotorsCalibrationData;

export type MotorsCalibrationData = {
  motors: Pick<MotorConfig, "calibration_direction">[];
};

export interface LEDConfig {
  interval: number | null;
  pin: number | string | null;
  name: string | null;
}
export interface Data extends ServoData, MotorsData {
  schema_version: number;
  motion_control: MotionControlConfig;
  ackermann_odometry: AckermannOdometryConfig;
  localization_sensors: LocalizationSensorsConfig;
  lidar_safety: LidarSafetyConfig;
  led: LEDConfig;
  batteries: Battery[];
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
  enabled: true,
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
    schema_version: 5,
    motion_control: {
      enabled: false,
      control_frequency_hz: 20,
      command_timeout_ms: 250,
      max_forward_speed_mps: null,
      max_reverse_speed_mps: null,
    },
    ackermann_odometry: {
      enabled: false,
      wheelbase_m: null,
      wheel_radius_m: null,
      encoder_ticks_per_revolution: null,
      gear_ratio: 1.0,
      max_steering_age_ms: 250,
    },
    localization_sensors: {
      lidar: {
        enabled: false,
        driver: "rplidar_c1",
        port: "/dev/ttyUSB0",
        baudrate: 460800,
        timeout_s: 1,
        frame_id: "laser",
        transform: {
          x_m: 0,
          y_m: 0,
          z_m: 0,
          roll_rad: 0,
          pitch_rad: 0,
          yaw_rad: 0,
        },
        range_min_m: null,
        range_max_m: null,
        angular_resolution_deg: 1,
        min_measurements_per_scan: 50,
      },
      imu: {
        enabled: false,
        driver: "sh3001",
        bus: 1,
        address: "0x36",
        frame_id: "imu",
        transform: {
          x_m: 0,
          y_m: 0,
          z_m: 0,
          roll_rad: 0,
          pitch_rad: 0,
          yaw_rad: 0,
        },
        sample_frequency_hz: 100,
        accelerometer_range_g: 2,
        gyroscope_range_dps: 2000,
      },
      encoder: {
        enabled: false,
        driver: "external",
        frame_id: "encoder",
        sample_frequency_hz: 100,
      },
    },
    lidar_safety: {
      enabled: false,
      front_half_angle_deg: 35,
      stop_distance_m: null,
      slow_distance_m: null,
      scan_timeout_ms: 500,
      min_obstacle_points: 2,
    },
    cam_pan_servo: defaultServo,
    cam_tilt_servo: defaultServo,
    steering_servo: defaultServo,
    motors: [{ ...motorDefaults }, { ...motorDefaults }],
    led: ledDefaults,
    batteries: [],
  },
};

export const useStore = defineStore("robot", {
  state: () => ({ ...defaultState }),

  getters: {
    maxSpeed({ data }) {
      const speeds = data.motors
        .filter((motor) => motor.enabled)
        .map((motor) => motor.max_speed || 100);
      return speeds.length ? Math.min(...speeds) : 100;
    },
    calibration({ data }) {
      const { steering_servo, cam_pan_servo, cam_tilt_servo, motors } = data;
      return {
        steering_servo_offset: steering_servo?.calibration_offset,
        cam_pan_servo_offset: cam_pan_servo?.calibration_offset,
        cam_tilt_servo_offset: cam_tilt_servo?.calibration_offset,
        motor_directions: motors.map((motor) => motor.calibration_direction),
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
      const { motors, ...servos } = payload;
      Object.entries(servos).forEach(([key, cal]) => {
        if (!cal) return;
        this.data[key as keyof ServoCalibrationData].calibration_offset =
          cal.calibration_offset;
      });

      let activeIndex = 0;
      this.data.motors.forEach((motor) => {
        if (!motor.enabled) return;
        const calibration = motors?.[activeIndex++];
        if (calibration) {
          motor.calibration_direction = calibration.calibration_direction;
        }
      });
    },
  },
});
