import { robotApi } from "@/api";

export type CalibrationKind =
  | "wheel_distance"
  | "speed"
  | "imu_bias"
  | "steering_center"
  | "steering_range"
  | "stopping";
export interface Trial {
  id: string;
  kind: CalibrationKind;
  accepted: boolean;
  reason: string;
  direction: "forward" | "reverse";
  power_percent: number;
  duration_s: number;
  distance_m: number | null;
  mean_speed_mps: number | null;
  minimum_speed_mps: number | null;
  maximum_speed_mps: number | null;
  distance_per_tick_m: number | null;
  gyro_bias_radps: number | null;
  sensor_angle_deg: number | null;
  steering_degrees: number | null;
  stopping_distance_m: number | null;
}
export interface CalibrationStatus {
  active: boolean;
  session_id: string | null;
  kind: CalibrationKind;
  driving: boolean;
  elapsed_s: number;
  max_power_percent: number;
  encoder_ticks: number | null;
  wall_distance_m: number | null;
  gyro_radps: number | null;
  sensor_angle_deg: number | null;
  blockers: string[];
  trials: Trial[];
  saved_config?: Record<string, unknown>;
}
export const calibrationPath = "px/api/calibration";
export const calibrationError = (error: unknown): string => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;
  if (Array.isArray(detail))
    return detail
      .map((item: { msg?: string; loc?: (string | number)[] }) => {
        const field = item.loc?.at(-1);
        const labels: Record<string, string> = {
          power_percent: "Motor power (%)",
          stop_distance_m: "Stop boundary (m)",
          max_duration_s: "Maximum drive time (s)",
          measured_distance_m: "Travel distance (m)",
          measured_wheel_angle_deg: "Measured wheel angle (°)",
          steering_degrees: "Steering command (°)",
        };
        return `${labels[String(field)] ?? "Measurement"}: ${item.msg?.replace(/^Value error, /, "") ?? "Enter a valid value"}`;
      })
      .join(" ");
  return typeof detail === "string"
    ? detail
    : "The robot did not respond. Check its connection before starting another trial.";
};

/** A release sends its own sequenced command even while a hold is in flight. */
export class CalibrationLease {
  private sequence = 0;
  private held = false;
  private pending = false;
  private closed = false;
  steeringDegrees = 0;
  constructor(
    readonly id: string,
    private update: (status: CalibrationStatus) => void,
    private failed: (message: string) => void,
  ) {}

  async heartbeat(force = false): Promise<void> {
    if (this.closed || (this.pending && !force)) return;
    this.pending = true;
    const sequence = ++this.sequence;
    try {
      const status = await robotApi.post<CalibrationStatus>(
        `${calibrationPath}/${this.id}/heartbeat`,
        {
          sequence,
          drive: this.held,
          steering_degrees: this.steeringDegrees,
        },
      );
      if (this.closed || sequence !== this.sequence) return;
      if (!status.active) this.close();
      this.update(status);
    } catch (error) {
      if (this.closed || sequence !== this.sequence) return;
      this.close();
      // Stop immediately if possible; the robot's heartbeat deadline is the fallback.
      void robotApi
        .post(`${calibrationPath}/${this.id}/cancel`)
        .catch(() => {});
      this.failed(calibrationError(error));
    } finally {
      if (sequence === this.sequence) this.pending = false;
    }
  }
  hold() {
    if (!this.closed) {
      this.held = true;
      void this.heartbeat(true);
    }
  }
  release() {
    this.held = false;
    return this.heartbeat(true);
  }
  close() {
    this.closed = true;
    this.held = false;
  }
}
