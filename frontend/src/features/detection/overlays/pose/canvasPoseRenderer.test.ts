import { describe, expect, it, vi } from "vitest";
import {
  drawKeypointCircle,
  isVisibleKeypoint,
  renderMeshLine,
} from "@/features/detection/overlays/pose/canvasPoseRenderer";
import type { SkeletonLineSpec } from "@/features/detection/overlays/pose/util";
import { scaleKeypoints } from "@/features/detection/overlays/pose/util";

const createContext = () =>
  ({
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    lineWidth: 4,
    strokeStyle: "",
    fillStyle: "",
  }) as unknown as CanvasRenderingContext2D;

describe("canvas pose keypoint visibility", () => {
  it.each([
    [{ x: 0, y: 1 }, true],
    [{ x: 10, y: 10 }, true],
    [{ x: -1, y: 10 }, false],
    [{ x: 10, y: 0 }, false],
    [{ x: 10, y: -1 }, false],
    [{ x: 10, y: 10, confidence: 0.0199 }, false],
    [{ x: 10, y: 10, confidence: 0.02 }, true],
    [undefined, false],
  ])("checks keypoint %o", (keypoint, expected) => {
    expect(isVisibleKeypoint(keypoint)).toBe(expected);
  });

  it("uses a supplied confidence threshold", () => {
    expect(isVisibleKeypoint({ x: 10, y: 10, confidence: 0.2 }, 0.5)).toBe(
      false,
    );
    expect(isVisibleKeypoint({ x: 10, y: 10, confidence: 0.5 }, 0.5)).toBe(
      true,
    );
  });

  it("preserves confidence while scaling keypoint coordinates", () => {
    expect(scaleKeypoints(2, 3, [{ x: 10, y: 20, confidence: 0.25 }])).toEqual([
      { x: 20, y: 60, confidence: 0.25 },
    ]);
  });

  it("does not draw a circle for a missing keypoint", () => {
    const ctx = createContext();

    drawKeypointCircle(ctx, { x: 0, y: 0 }, 5, 16, () => "#fff");

    expect(ctx.beginPath).not.toHaveBeenCalled();
    expect(ctx.arc).not.toHaveBeenCalled();
  });

  it("does not draw a line with a missing endpoint", () => {
    const ctx = createContext();
    const lineSpec: SkeletonLineSpec = [0, 1, 40, "#fff", false, "head"];

    renderMeshLine(
      ctx,
      [
        { x: 10, y: 10 },
        { x: 0, y: 0 },
      ],
      lineSpec,
      4,
    );

    expect(ctx.beginPath).not.toHaveBeenCalled();
    expect(ctx.moveTo).not.toHaveBeenCalled();
  });
});
