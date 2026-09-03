import { describe, expect, it } from "vitest";
import {
  calculatePoseError,
  canvasToWorld,
  gridToCanvas,
  worldPointToOdom,
  worldToGrid,
  worldYawToCanvas,
  worldYawToOdom,
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

  it("converts a canvas click back into map-frame metres", () => {
    const map = grid();

    expect(canvasToWorld(map, 150, 25, 200, 100)).toEqual({ x: 2.5, y: 2.5 });
    expect(canvasToWorld(map, 200, 25, 200, 100)).toBeNull();
  });

  it("converts clicks through a rotated map origin", () => {
    const map = grid(Math.PI / 2);
    const point = canvasToWorld(map, 120, 70, 200, 100);

    expect(point?.x).toBeCloseTo(-8);
    expect(point?.y).toBeCloseTo(1);
  });

  it("rejects positions outside the bounded grid", () => {
    expect(worldToGrid(grid(), 6, 0)).toBeNull();
  });

  it("expresses simulator world geometry relative to the configured odom origin", () => {
    const odomPoint = worldPointToOdom(
      { x: 2, y: 4 },
      { x: 2, y: 3, yaw: Math.PI / 2 },
    );

    expect(odomPoint.x).toBeCloseTo(1);
    expect(odomPoint.y).toBeCloseTo(0);
    expect(worldYawToOdom(Math.PI, Math.PI / 2)).toBeCloseTo(Math.PI / 2);
  });

  it("compares estimated and reference poses across the angle boundary", () => {
    const error = calculatePoseError(
      { x: 3, y: 4, yaw: Math.PI - 0.1 },
      { x: 0, y: 0, yaw: -Math.PI + 0.1 },
    );

    expect(error.positionM).toBe(5);
    expect(error.headingRad).toBeCloseTo(0.2);
  });
});
