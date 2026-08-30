import { describe, expect, it } from "vitest";
import {
  gridToCanvas,
  worldToGrid,
  worldYawToCanvas,
} from "@/features/autonomy/mapGeometry";
import type { OccupancyGrid } from "@/features/autonomy";

const grid = (originYaw = 0): OccupancyGrid => ({
  header: {
    sequence: 1,
    frame_id: "odom",
    timestamp_monotonic_ns: 1,
    source_timestamp_ns: null,
  },
  width: 10,
  height: 10,
  resolution_m: 1,
  origin_x_m: -5,
  origin_y_m: -5,
  origin_yaw_rad: originYaw,
  data: Array(100).fill(-1),
});

describe("occupancy map geometry", () => {
  it("maps the odom origin to the center of the canvas", () => {
    const map = grid();
    const point = worldToGrid(map, 0, 0);

    expect(point).toEqual({ x: 5, y: 5 });
    expect(gridToCanvas(map, point!, 200, 100)).toEqual({ x: 100, y: 50 });
  });

  it("accounts for a rotated map origin", () => {
    const map = grid(Math.PI / 2);
    const point = worldToGrid(map, -7, -4);

    expect(point?.x).toBeCloseTo(1);
    expect(point?.y).toBeCloseTo(2);
    expect(worldYawToCanvas(map, Math.PI / 2)).toBeCloseTo(0);
  });

  it("rejects positions outside the bounded grid", () => {
    expect(worldToGrid(grid(), 6, 0)).toBeNull();
  });
});
