import type { LaserScanTelemetry } from "@/features/autonomy/store";
import type { StaticTransformConfig } from "@/features/settings/stores/robot";

export interface ProjectedLidarPoint {
  x_m: number;
  y_m: number;
  distance_m: number;
  intensity: number | null;
}

export const projectLaserScan = (
  scan: LaserScanTelemetry,
  transform: StaticTransformConfig,
): ProjectedLidarPoint[] => {
  const cosYaw = Math.cos(transform.yaw_rad);
  const sinYaw = Math.sin(transform.yaw_rad);
  const points: ProjectedLidarPoint[] = [];

  scan.ranges_m.forEach((range, index) => {
    if (
      range === null ||
      !Number.isFinite(range) ||
      range < scan.range_min_m ||
      range > scan.range_max_m
    ) {
      return;
    }
    const angle = scan.angle_min_rad + index * scan.angle_increment_rad;
    const sensorX = range * Math.cos(angle);
    const sensorY = range * Math.sin(angle);
    const x = transform.x_m + cosYaw * sensorX - sinYaw * sensorY;
    const y = transform.y_m + sinYaw * sensorX + cosYaw * sensorY;
    points.push({
      x_m: x,
      y_m: y,
      distance_m: Math.hypot(x, y),
      intensity: scan.intensities?.[index] ?? null,
    });
  });

  return points;
};
