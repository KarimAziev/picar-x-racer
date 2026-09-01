import type { OccupancyGrid } from "@/features/autonomy/store";

export interface Point2D {
  x: number;
  y: number;
}

export interface Pose2D extends Point2D {
  yaw: number;
}

export const worldPointToOdom = (
  point: Point2D,
  odomOriginInWorld: Pose2D,
): Point2D => {
  const dx = point.x - odomOriginInWorld.x;
  const dy = point.y - odomOriginInWorld.y;
  const cos = Math.cos(odomOriginInWorld.yaw);
  const sin = Math.sin(odomOriginInWorld.yaw);
  return {
    x: cos * dx + sin * dy,
    y: -sin * dx + cos * dy,
  };
};

export const normalizeAngle = (angle: number) => {
  const wrapped = ((angle + Math.PI) % (2 * Math.PI)) - Math.PI;
  return wrapped < -Math.PI ? wrapped + 2 * Math.PI : wrapped;
};

export const worldYawToOdom = (worldYaw: number, odomOriginYaw: number) =>
  normalizeAngle(worldYaw - odomOriginYaw);

export const worldToGridUnbounded = (
  grid: OccupancyGrid,
  x: number,
  y: number,
): Point2D => {
  const dx = x - grid.origin_x_m;
  const dy = y - grid.origin_y_m;
  const cos = Math.cos(grid.origin_yaw_rad);
  const sin = Math.sin(grid.origin_yaw_rad);
  const gridX = (cos * dx + sin * dy) / grid.resolution_m;
  const gridY = (-sin * dx + cos * dy) / grid.resolution_m;
  return { x: gridX, y: gridY };
};

export const worldToGrid = (
  grid: OccupancyGrid,
  x: number,
  y: number,
): Point2D | null => {
  const point = worldToGridUnbounded(grid, x, y);
  if (
    point.x < 0 ||
    point.y < 0 ||
    point.x >= grid.width ||
    point.y >= grid.height
  ) {
    return null;
  }
  return point;
};

export const gridToCanvas = (
  grid: OccupancyGrid,
  point: Point2D,
  canvasWidth: number,
  canvasHeight: number,
): Point2D => ({
  x: (point.x / grid.width) * canvasWidth,
  y: canvasHeight - (point.y / grid.height) * canvasHeight,
});

export const worldYawToCanvas = (grid: OccupancyGrid, yawRad: number) =>
  -(yawRad - grid.origin_yaw_rad);
