import type { Data } from "@/features/settings/stores/robot";
import type { GuideKind } from "@/features/calibration/guides";
import { isNil, isNumber } from "@/util/guards";
import { getObjProp, isObjectEquals } from "@/util/obj";
import type { FlattenObject } from "@/util/ts-helpers";

type JsonValue =
  string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
export type CalibrationStep =
  Exclude<GuideKind, "mounting"> | "lidar_mount" | "imu_mount";
export type CalibrationProgress = Partial<
  Record<CalibrationStep, Record<string, JsonValue>>
>;
export type GuideState = "complete" | "review" | "partial" | "todo";
export interface GuideProgress {
  state: GuideState;
  label: string;
  detail: string;
}

function completed(data: Data, step: CalibrationStep): boolean {
  const snapshot = data.calibration_progress?.[step];
  if (isNil(snapshot) || Object.keys(snapshot).length === 0) return false;
  const current = Object.fromEntries(
    Object.keys(snapshot).map((path) => [
      path,
      getObjProp(path as keyof FlattenObject<Data>, data),
    ]),
  );
  return isObjectEquals(snapshot, current);
}

const positive = (value: number | null) => isNumber(value) && value > 0;

export function guideProgress(data: Data, kind: GuideKind): GuideProgress {
  if (kind === "mounting") {
    const lidar = completed(data, "lidar_mount");
    const imu = completed(data, "imu_mount");
    return {
      state: lidar && imu ? "complete" : lidar || imu ? "partial" : "review",
      label:
        lidar && imu
          ? "Completed"
          : lidar || imu
            ? "1 of 2 completed"
            : "Needs review",
      detail: `LiDAR: ${lidar ? "completed" : "needs review"} · IMU: ${imu ? "completed" : "needs review"}`,
    };
  }
  if (completed(data, kind)) {
    return {
      state: "complete",
      label: "Completed",
      detail: "Reviewed measurements saved.",
    };
  }
  const hasValues: Record<Exclude<GuideKind, "mounting">, boolean> = {
    body: [
      data.ackermann_odometry.wheelbase_m,
      data.navigation.body_length_m,
      data.navigation.body_width_m,
      data.navigation.rear_overhang_m,
    ].some((value) => !isNil(value)),
    wheel_distance: positive(data.ackermann_odometry.wheel_radius_m),
    steering_center: !isNil(data.steering_servo.calibration_offset),
    steering_range:
      data.localization_sensors.steering.calibration_points.length > 0,
    imu_bias: data.pose_estimation.imu_yaw_bias_radps !== 0,
    speed:
      data.motion_control.forward_speed_curve.length > 0 ||
      data.motion_control.reverse_speed_curve.length > 0,
    stopping: positive(data.lidar_safety.stop_distance_m),
  };
  const changed = !isNil(data.calibration_progress?.[kind]);
  return changed || hasValues[kind]
    ? {
        state: "review",
        label: "Needs review",
        detail: changed
          ? "Settings changed since this guide was completed."
          : "Values entered. Review and apply to confirm.",
      }
    : {
        state: "todo",
        label: "To do",
        detail: "Complete this guide to save measurements.",
      };
}
