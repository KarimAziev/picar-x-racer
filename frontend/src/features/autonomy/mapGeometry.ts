import type { OccupancyGrid } from "@/features/autonomy/store";

export interface Point2D {
  x: number;
  y: number;
}

export const worldToGrid = (
  grid: OccupancyGrid,
  x: number,
  y: number,
): Point2D | null => {
  const dx = x - grid.origin_x_m;
  const dy = y - grid.origin_y_m;
  const cos = Math.cos(grid.origin_yaw_rad);
  const sin = Math.sin(grid.origin_yaw_rad);
  const gridX = (cos * dx + sin * dy) / grid.resolution_m;
  const gridY = (-sin * dx + cos * dy) / grid.resolution_m;
  if (gridX < 0 || gridY < 0 || gridX >= grid.width || gridY >= grid.height) {
    return null;
  }
  return { x: gridX, y: gridY };
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
