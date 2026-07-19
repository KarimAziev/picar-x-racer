import type { ShallowRef } from "vue";
import { defineStore } from "pinia";
import { robotApi } from "@/api";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";
import { retrieveError } from "@/util/error";

export type SensorName = "lidar" | "imu" | "encoder";
export type TelemetryChannel = SensorName | "odometry" | "safety";

export interface SensorPublisherStatus {
  sensor: SensorName;
  enabled: boolean;
  running: boolean;
  published_messages: number;
  last_timestamp_monotonic_ns: number | null;
  error: string | null;
}

export interface LocalizationSensorStatus {
  sensors: SensorPublisherStatus[];
}

export interface MessageHeader {
  sequence: number;
  frame_id: string;
  timestamp_monotonic_ns: number;
  source_timestamp_ns: number | null;
}

interface BaseTelemetryEnvelope<Channel extends TelemetryChannel, Payload> {
  channel: Channel;
  topic: string;
  payload: Payload;
}

export interface LaserScanTelemetry {
  header: MessageHeader;
  angle_min_rad: number;
  angle_max_rad: number;
  angle_increment_rad: number;
  range_min_m: number;
  range_max_m: number;
  ranges_m: Array<number | null>;
  intensities: number[] | null;
}

export interface ImuTelemetry {
  header: MessageHeader;
  angular_velocity_z_radps: number;
  acceleration_x_mps2: number;
  acceleration_y_mps2: number;
  acceleration_z_mps2: number;
  yaw_rad: number | null;
}

export interface EncoderTelemetry {
  header: MessageHeader;
  ticks: number;
  delta_ticks: number;
}

export interface OdometryTelemetry {
  header: MessageHeader;
  child_frame_id: string;
  x_m: number;
  y_m: number;
  yaw_rad: number;
  linear_speed_mps: number;
  yaw_rate_radps: number;
}

export interface SafetyTelemetry {
  header: MessageHeader;
  forward_blocked: boolean;
  max_forward_speed_mps: number;
  nearest_obstacle_m: number | null;
  considered_points: number;
  reason: string | null;
}

export type TelemetryEnvelope =
  | BaseTelemetryEnvelope<"lidar", LaserScanTelemetry>
  | BaseTelemetryEnvelope<"imu", ImuTelemetry>
  | BaseTelemetryEnvelope<"encoder", EncoderTelemetry>
  | BaseTelemetryEnvelope<"odometry", OdometryTelemetry>
  | BaseTelemetryEnvelope<"safety", SafetyTelemetry>;

export interface State {
  loading: boolean;
  error: string | null;
  sensors: SensorPublisherStatus[];
  latest: Partial<Record<TelemetryChannel, TelemetryEnvelope>>;
  connection: ShallowRef<WebSocketModel> | null;
}

const defaultState: State = {
  loading: false,
  error: null,
  sensors: [],
  latest: {},
  connection: null,
};

export const useAutonomyStore = defineStore("autonomy-telemetry", {
  state: (): State => ({ ...defaultState, latest: {} }),
  getters: {
    connected({ connection }) {
      return connection?.connected.value ?? false;
    },
  },
  actions: {
    async refreshStatus() {
      try {
        this.loading = this.sensors.length === 0;
        const status = await robotApi.get<LocalizationSensorStatus>(
          "/px/api/sensors/status",
        );
        this.sensors = status.sensors;
        this.error = null;
      } catch (error) {
        this.error = retrieveError(error).text;
      } finally {
        this.loading = false;
      }
    },

    initialize() {
      void this.refreshStatus();
      if (this.connection) {
        return;
      }
      const model = useWebSocket({
        url: "px/ws/telemetry",
        port: +(import.meta.env.VITE_WS_APP_PORT || "8001"),
        logPrefix: "robot telemetry",
        queueMessages: false,
        onMessage: (message: TelemetryEnvelope) => {
          this.latest[message.channel] = message;
        },
      });
      this.connection = model;
      model.initWS();
    },

    cleanup() {
      this.connection?.cleanup();
      this.connection = null;
    },
  },
});
