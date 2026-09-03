import { unref } from "vue";
import type { ShallowRef } from "vue";
import { defineStore } from "pinia";
import { robotApi } from "@/api";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";
import { retrieveError } from "@/util/error";

export type SensorName = "lidar" | "imu" | "encoder";
export type TelemetryChannel =
  SensorName | "odometry" | "localization" | "safety" | "simulation";

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

export type LocalizationFusionMode = "wheel" | "wheel_imu" | "corrected";

export interface LocalizationPoseTelemetry extends OdometryTelemetry {
  position_variance_m2: number;
  yaw_variance_rad2: number;
  fusion_mode: LocalizationFusionMode;
  last_correction_source: string | null;
}

export interface LocalizationRuntimeStatus {
  enabled: boolean;
  running: boolean;
  published_updates: number;
  imu_updates_used: number;
  imu_updates_rejected: number;
  corrections_applied: number;
  corrections_rejected: number;
  last_position_innovation_m: number | null;
  last_heading_innovation_rad: number | null;
  latest_pose: LocalizationPoseTelemetry | null;
  error: string | null;
}

export interface PoseObservationTelemetry {
  header: MessageHeader;
  x_m: number;
  y_m: number;
  yaw_rad: number;
  position_variance_m2: number;
  yaw_variance_rad2: number;
  source: string;
}

export interface ScanMatchingRuntimeStatus {
  enabled: boolean;
  running: boolean;
  scans_received: number;
  matches_published: number;
  rejected_missing_pose: number;
  rejected_pose_timing: number;
  rejected_insufficient_points: number;
  rejected_quality: number;
  last_mean_error_m: number | null;
  last_prior_mean_error_m: number | null;
  last_valid_points: number;
  last_candidates_evaluated: number;
  latest_observation: PoseObservationTelemetry | null;
  last_rejection: string | null;
  error: string | null;
}

export interface SafetyTelemetry {
  header: MessageHeader;
  forward_blocked: boolean;
  max_forward_speed_mps: number;
  nearest_obstacle_m: number | null;
  considered_points: number;
  reason: string | null;
}

export interface SimulationState {
  header: MessageHeader;
  x_m: number;
  y_m: number;
  yaw_rad: number;
  linear_speed_mps: number;
  steering_angle_rad: number;
  yaw_rate_radps: number;
  longitudinal_acceleration_mps2: number;
  lateral_acceleration_mps2: number;
  encoder_ticks: number;
  collision: boolean;
}

export interface SimulationPose2D {
  x_m: number;
  y_m: number;
  yaw_rad: number;
}

export interface SimulationWorldSegment {
  start_x_m: number;
  start_y_m: number;
  end_x_m: number;
  end_y_m: number;
}

export interface SimulationWorldGeometry {
  scenario: string;
  frame_id: string;
  segments: SimulationWorldSegment[];
}

export interface SimulationSensorImperfectionStatus {
  enabled: boolean;
  random_seed: number;
  encoder_scale_error_percent: number;
  encoder_noise_stddev_ticks: number;
  steering_bias_deg: number;
  steering_noise_stddev_deg: number;
  imu_yaw_rate_bias_radps: number;
  imu_yaw_rate_noise_stddev_radps: number;
  lidar_range_noise_stddev_m: number;
  lidar_dropout_probability: number;
}

export interface SimulationRuntimeStatus {
  enabled: boolean;
  running: boolean;
  physical_drive_isolated: boolean;
  published_updates: number;
  lidar_published_updates: number;
  world: SimulationWorldGeometry | null;
  odom_origin_in_world: SimulationPose2D | null;
  sensor_imperfections: SimulationSensorImperfectionStatus | null;
  latest_state: SimulationState | null;
  error: string | null;
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

export type AutonomousActionState =
  "idle" | "running" | "succeeded" | "blocked" | "failed" | "canceled";

export type RelativeActionType = "distance" | "arc";

export interface RelativeMotionStatus {
  available: boolean;
  state: AutonomousActionState;
  action_id: string | null;
  action_type: RelativeActionType | null;
  distance_m: number | null;
  requested_speed_mps: number | null;
  progress_m: number;
  remaining_m: number | null;
  steering_angle_deg: number | null;
  max_abs_steering_angle_deg: number | null;
  target_yaw_rad: number | null;
  yaw_progress_rad: number | null;
  reason: string | null;
}

export type TelemetryEnvelope =
  | BaseTelemetryEnvelope<"lidar", LaserScanTelemetry>
  | BaseTelemetryEnvelope<"imu", ImuTelemetry>
  | BaseTelemetryEnvelope<"encoder", EncoderTelemetry>
  | BaseTelemetryEnvelope<"odometry", OdometryTelemetry>
  | BaseTelemetryEnvelope<"localization", LocalizationPoseTelemetry>
  | BaseTelemetryEnvelope<"safety", SafetyTelemetry>
  | BaseTelemetryEnvelope<"simulation", SimulationState>;

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
  relativeMotion: RelativeMotionStatus | null;
  relativeMotionLoading: boolean;
  relativeMotionError: string | null;
  simulation: SimulationRuntimeStatus | null;
  simulationLoading: boolean;
  simulationResetting: boolean;
  simulationError: string | null;
  simulationLastUpdatedAt: number | null;
  localization: LocalizationRuntimeStatus | null;
  localizationError: string | null;
  scanMatching: ScanMatchingRuntimeStatus | null;
  scanMatchingError: string | null;
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
  relativeMotion: null,
  relativeMotionLoading: false,
  relativeMotionError: null,
  simulation: null,
  simulationLoading: false,
  simulationResetting: false,
  simulationError: null,
  simulationLastUpdatedAt: null,
  localization: null,
  localizationError: null,
  scanMatching: null,
  scanMatchingError: null,
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

    async refreshRelativeMotion() {
      try {
        this.relativeMotion = await robotApi.get<RelativeMotionStatus>(
          "/px/api/autonomy/relative-motion",
        );
        this.relativeMotionError = null;
      } catch (error) {
        this.relativeMotionError = retrieveError(error).text;
      }
    },

    async startRelativeDistance(distanceM: number, speedMps: number) {
      try {
        this.relativeMotionLoading = true;
        this.relativeMotion = await robotApi.post<RelativeMotionStatus>(
          "/px/api/autonomy/relative-motion/distance",
          { distance_m: distanceM, speed_mps: speedMps },
        );
        this.relativeMotionError = null;
      } catch (error) {
        this.relativeMotionError = retrieveError(error).text;
      } finally {
        this.relativeMotionLoading = false;
      }
    },

    async startRelativeArc(
      distanceM: number,
      speedMps: number,
      steeringAngleDeg: number,
    ) {
      try {
        this.relativeMotionLoading = true;
        this.relativeMotion = await robotApi.post<RelativeMotionStatus>(
          "/px/api/autonomy/relative-motion/arc",
          {
            distance_m: distanceM,
            speed_mps: speedMps,
            steering_angle_deg: steeringAngleDeg,
          },
        );
        this.relativeMotionError = null;
      } catch (error) {
        this.relativeMotionError = retrieveError(error).text;
      } finally {
        this.relativeMotionLoading = false;
      }
    },

    async cancelRelativeMotion() {
      try {
        this.relativeMotionLoading = true;
        this.relativeMotion = await robotApi.post<RelativeMotionStatus>(
          "/px/api/autonomy/relative-motion/cancel",
        );
        this.relativeMotionError = null;
      } catch (error) {
        this.relativeMotionError = retrieveError(error).text;
      } finally {
        this.relativeMotionLoading = false;
      }
    },

    async refreshSimulation() {
      try {
        this.simulationLoading = this.simulation === null;
        this.simulation = await robotApi.get<SimulationRuntimeStatus>(
          "/px/api/autonomy/simulation",
        );
        this.simulationError = null;
        this.simulationLastUpdatedAt = Date.now();
      } catch (error) {
        this.simulationError = retrieveError(error).text;
      } finally {
        this.simulationLoading = false;
      }
    },

    async refreshLocalization() {
      try {
        const status = await robotApi.get<LocalizationRuntimeStatus>(
          "/px/api/autonomy/localization",
        );
        this.localization = status;
        if (!status.enabled) delete this.latest.localization;
        this.localizationError = null;
      } catch (error) {
        this.localizationError = retrieveError(error).text;
      }
    },

    async refreshScanMatching() {
      try {
        this.scanMatching = await robotApi.get<ScanMatchingRuntimeStatus>(
          "/px/api/autonomy/localization/scan-matching",
        );
        this.scanMatchingError = null;
      } catch (error) {
        // Keep the last successful quality sample visible while reporting that
        // its health snapshot is stale.
        this.scanMatchingError = retrieveError(error).text;
      }
    },

    async resetSimulation() {
      try {
        this.simulationResetting = true;
        this.simulation = await robotApi.post<SimulationRuntimeStatus>(
          "/px/api/autonomy/simulation/reset",
        );
        this.mapClearGeneration += 1;
        await Promise.all([
          this.refreshMappingSession(),
          this.refreshLocalMap(),
          this.refreshScanMatching(),
        ]);
        this.simulationError = null;
        this.simulationLastUpdatedAt = Date.now();
      } catch (error) {
        this.simulationError = retrieveError(error).text;
      } finally {
        this.simulationResetting = false;
      }
    },

    initialize() {
      this.consumers += 1;
      void this.refreshStatus();
      void this.refreshLocalization();
      void this.refreshScanMatching();
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
