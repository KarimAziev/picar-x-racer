import { unref } from "vue";
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
  left: EncoderReadingTelemetry | null;
  right: EncoderReadingTelemetry | null;
}

export interface EncoderReadingTelemetry {
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

export interface OccupancyGrid {
  header: MessageHeader;
  width: number;
  height: number;
  resolution_m: number;
  origin_x_m: number;
  origin_y_m: number;
  origin_yaw_rad: number;
  data: number[];
}

export type MappingSessionState = "disabled" | "idle" | "active" | "paused";

export interface MappingSessionStatus {
  enabled: boolean;
  state: MappingSessionState;
  session_id: number;
  map_sequence: number;
  scans_received: number;
  scans_inserted: number;
  returns_inserted: number;
  ignored_inactive_scans: number;
  rejected_missing_odometry: number;
  rejected_stale_odometry: number;
  has_map: boolean;
}

export type MappingSessionAction =
  "start" | "pause" | "finish" | "clear" | "reset";

export type TelemetryEnvelope =
  | BaseTelemetryEnvelope<"lidar", LaserScanTelemetry>
  | BaseTelemetryEnvelope<"imu", ImuTelemetry>
  | BaseTelemetryEnvelope<"encoder", EncoderTelemetry>
  | BaseTelemetryEnvelope<"odometry", OdometryTelemetry>
  | BaseTelemetryEnvelope<"safety", SafetyTelemetry>;

export interface State {
  loading: boolean;
  error: string | null;
  mapError: string | null;
  mappingActionLoading: boolean;
  mappingActionError: string | null;
  sensors: SensorPublisherStatus[];
  localMap: OccupancyGrid | null;
  mappingSession: MappingSessionStatus | null;
  mapClearGeneration: number;
  latest: Partial<Record<TelemetryChannel, TelemetryEnvelope>>;
  connection: ShallowRef<WebSocketModel> | null;
  consumers: number;
}

const defaultState: State = {
  loading: false,
  error: null,
  mapError: null,
  mappingActionLoading: false,
  mappingActionError: null,
  sensors: [],
  localMap: null,
  mappingSession: null,
  mapClearGeneration: 0,
  latest: {},
  connection: null,
  consumers: 0,
};

export const useAutonomyStore = defineStore("autonomy-telemetry", {
  state: (): State => ({ ...defaultState, latest: {} }),
  getters: {
    connected({ connection }) {
      // Pinia/Vue unwrap nested refs when the websocket model is stored in
      // reactive state. `unref` handles both that runtime boolean and the Ref
      // shape used by the websocket composable itself.
      return unref(connection?.connected) ?? false;
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

    async refreshLocalMap() {
      try {
        this.localMap = await robotApi.get<OccupancyGrid>(
          "/px/api/map/current",
        );
        this.mapError = null;
      } catch (error) {
        const status = (error as { response?: { status?: number } }).response
          ?.status;
        if (status === 404) {
          this.localMap = null;
          this.mapError = null;
        } else {
          this.mapError = retrieveError(error).text;
        }
      }
    },

    async refreshMappingSession() {
      try {
        this.mappingSession = await robotApi.get<MappingSessionStatus>(
          "/px/api/map/session",
        );
        this.mappingActionError = null;
      } catch (error) {
        this.mappingActionError = retrieveError(error).text;
      }
    },

    async runMappingAction(action: MappingSessionAction) {
      try {
        this.mappingActionLoading = true;
        this.mappingSession = await robotApi.post<MappingSessionStatus>(
          `/px/api/map/session/${action}`,
        );
        this.mappingActionError = null;
        if (action === "clear" || action === "reset") {
          this.mapClearGeneration += 1;
          await this.refreshLocalMap();
        }
      } catch (error) {
        this.mappingActionError = retrieveError(error).text;
      } finally {
        this.mappingActionLoading = false;
      }
    },

    initialize() {
      this.consumers += 1;
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
      this.consumers = Math.max(0, this.consumers - 1);
      if (this.consumers > 0) {
        return;
      }
      this.connection?.cleanup();
      this.connection = null;
    },
  },
});
