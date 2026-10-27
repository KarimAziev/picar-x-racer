import type { DepthMapData } from "../interface";
import type { DetectionOverlayHandler } from "./overlay";
import { setupCtx } from "./util";

export function depthPixels(depth: DepthMapData): Uint8ClampedArray<ArrayBuffer> {
  const bytes = atob(depth.data);
  const count = depth.width * depth.height;
  if (bytes.length !== count) throw new Error("Invalid depth map dimensions");
  const pixels = new Uint8ClampedArray(count * 4);
  for (let i = 0; i < count; i++) {
    const value = bytes.charCodeAt(i);
    pixels.set([255 - value, 255 - Math.abs(2 * value - 255), value, 191], i * 4);
  }
  return pixels;
}

let bitmap: HTMLCanvasElement | undefined;
let previous: DepthMapData | undefined;
export const drawDepthOverlay: DetectionOverlayHandler = (
  canvas, elem, _detections, font, color, _lines, _keypoints, _semantic, _threshold, depth,
) => {
  const { ctx } = setupCtx(canvas, elem, font, color);
  if (!ctx || !depth || depth.width <= 0 || depth.height <= 0) return;
  bitmap ??= document.createElement("canvas");
  if (previous !== depth) {
    if (bitmap.width !== depth.width) bitmap.width = depth.width;
    if (bitmap.height !== depth.height) bitmap.height = depth.height;
    const bitmapContext = bitmap.getContext("2d");
    if (!bitmapContext) return;
    bitmapContext.putImageData(new ImageData(depthPixels(depth), depth.width, depth.height), 0, 0);
    previous = depth;
  }
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
};
