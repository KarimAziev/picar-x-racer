import { describe, expect, it } from "vitest";
import { projectLaserScan } from "@/features/autonomy/lidarPreview";
import type { LaserScanTelemetry } from "@/features/autonomy/store";
import type { StaticTransformConfig } from "@/features/settings/stores/robot";

const scan: LaserScanTelemetry = {
  header: {
    sequence: 1,
    frame_id: "laser",
    timestamp_monotonic_ns: 100,
    source_timestamp_ns: null,
  },
  angle_min_rad: 0,
  angle_max_rad: Math.PI / 2,
  angle_increment_rad: Math.PI / 2,
  range_min_m: 0.1,
  range_max_m: 10,
  ranges_m: [1, null],
  intensities: [12, 0],
};

const transform: StaticTransformConfig = {
  x_m: 0.2,
  y_m: -0.1,
  z_m: 0,
  roll_rad: 0,
  pitch_rad: 0,
  yaw_rad: Math.PI / 2,
};

describe("LiDAR preview projection", () => {
  it("projects finite sensor returns into base_link", () => {
    const points = projectLaserScan(scan, transform);

    expect(points).toHaveLength(1);
    expect(points[0].x_m).toBeCloseTo(0.2);
    expect(points[0].y_m).toBeCloseTo(0.9);
    expect(points[0].intensity).toBe(12);
  });

  it("rejects values outside the advertised scan range", () => {
    const points = projectLaserScan(
      { ...scan, ranges_m: [0.05, 11] },
      transform,
    );

    expect(points).toEqual([]);
  });
});
