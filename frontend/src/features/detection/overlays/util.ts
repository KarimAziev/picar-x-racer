import { isImage } from "@/util/guards";
import { drawKeypoints } from "@/features/detection/overlays/pose/canvasPoseRenderer";
import type {
  DetectionResult,
  OverlayLinesParams,
  KeypointsParams,
} from "@/features/detection/interface";
import {
  MAX_LINE_WIDTH,
  LINE_WIDTH_SCALING_FACTOR,
} from "@/features/detection/overlays/config";
import { Nullable } from "@/util/ts-helpers";
import { BODY_PARTS } from "@/features/detection/enums";

/**
 * Draws a label with confidence percentage above the bounding box on the canvas.
 * @param label - The label/classification of the detected object.
 * @param confidence - The confidence score as a number between 0 and 1.
 * @param ctx - The canvas rendering context.
 * @param x1 - The x-coordinate of the top-left corner of the bounding box.
 * @param y1 - The y-coordinate of the top-left corner of the bounding box.
 * @example
 * const canvas = document.getElementById("canvas") as HTMLCanvasElement;
 * const ctx = canvas.getContext("2d");
 * drawLabelWithConfidence("Car", 0.95, ctx, 100, 50);
 */
export const drawLabelWithConfidence = (
  label: string,
  confidence: number,
  ctx: CanvasRenderingContext2D,
  x1: number,
  y1: number,
) => {
  const y = parseFloat(ctx.font);

  ctx.fillText(
    `${label.toUpperCase()}: ${(confidence * 100).toFixed(1)}%`,
    x1 + 5,
    y1 + y,
  );
};

/**
 * Draws a bounding box on the canvas for the detected object.
 * Calls `drawLabelWithConfidence` to display the label and confidence.
 * @param ctx - The canvas rendering context.
 * @param scaleX - Horizontal scaling factor for the bounding box coordinates.
 * @param scaleY - Vertical scaling factor for the bounding box coordinates.
 * @param detection - The detection result containing the label, confidence, and bounding box.
 * @example
 * drawDetectionOverlay(ctx, 1, 1, { label: "Person", confidence: 0.87, bbox: [100, 100, 200, 300] });
 */
export const drawDetectionOverlay = (
  ctx: CanvasRenderingContext2D,
  scaleX: number,
  scaleY: number,
  detection: DetectionResult,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
) => {
  const { label, confidence, bbox, keypoints } = detection;
  if (bbox) {
    let [x1, y1, x2, y2] = bbox;

    x1 = x1 * scaleX;
    y1 = y1 * scaleY;
    x2 = x2 * scaleX;
    y2 = y2 * scaleY;

    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    drawLabelWithConfidence(label, confidence, ctx, x1, y1);
  }

  if (keypoints) {
    drawKeypoints(ctx, scaleX, scaleY, detection, poseLines, poseKeystrokes);
  }
};

/**
 * Draws crosshair lines (centered) within the bounding box for the detected object.
 * Calls `drawLabelWithConfidence` to display the label and confidence.
 * @param ctx - The canvas rendering context.
 * @param scaleX - Horizontal scaling factor for the bounding box coordinates.
 * @param scaleY - Vertical scaling factor for the bounding box coordinates.
 * @param detection - The detection result containing the label, confidence, and bounding box.
 * @example
 * drawDetectionCrosshair(ctx, 1, 1, { label: "Dog", confidence: 0.92, bbox: [50, 50, 150, 200] });
 */
export const drawDetectionCrosshair = (
  ctx: CanvasRenderingContext2D,
  scaleX: number,
  scaleY: number,
  detection: DetectionResult,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
) => {
  const { label, confidence, bbox, keypoints } = detection;

  const noseCoords = keypoints && keypoints[BODY_PARTS.NOSE];
  let [x1, y1, x2, y2] = bbox;

  x1 = x1 * scaleX;
  y1 = y1 * scaleY;
  x2 = x2 * scaleX;
  y2 = y2 * scaleY;

  let midX = (x1 + x2) / 2;
  let midY = (y1 + y2) / 2;

  if (noseCoords) {
    const noseCoords = keypoints[BODY_PARTS.NOSE];
    midX = noseCoords.x * scaleX;
    midY = noseCoords.y * scaleY;
  }

  ctx.beginPath();
  ctx.moveTo(x1, midY);
  ctx.lineTo(x2, midY);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(midX, y1);
  ctx.lineTo(midX, y2);
  ctx.stroke();
  drawLabelWithConfidence(label, confidence, ctx, x1, y1);
  if (keypoints) {
    drawKeypoints(ctx, scaleX, scaleY, detection, poseLines, poseKeystrokes);
  }
};

/**
 * Draws crosshair lines (centered) within the bounding box for the detected object of the full canvas width and height.
 * Calls `drawLabelWithConfidence` to display the label and confidence.
 * @param ctx - The canvas rendering context.
 * @param scaleX - Horizontal scaling factor for the bounding box coordinates.
 * @param scaleY - Vertical scaling factor for the bounding box coordinates.
 * @param detection - The detection result containing the label, confidence, and bounding box.
 * @example
 * drawFullDetectionCrosshair(ctx, 1, 1, { label: "Dog", confidence: 0.92, bbox: [50, 50, 150, 200] });
 */
export const drawFullDetectionCrosshair = (
  ctx: CanvasRenderingContext2D,
  scaleX: number,
  scaleY: number,
  detection: DetectionResult,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
) => {
  const { label, confidence, bbox, keypoints } = detection;
  let [x1, y1, x2, y2] = bbox;

  x1 = x1 * scaleX;
  y1 = y1 * scaleY;
  x2 = x2 * scaleX;
  y2 = y2 * scaleY;

  let midX = (x1 + x2) / 2;
  let midY = (y1 + y2) / 2;

  if (keypoints && keypoints[BODY_PARTS.NOSE]) {
    const noseCoords = keypoints[BODY_PARTS.NOSE];
    midX = noseCoords.x * scaleX;
    midY = noseCoords.y * scaleY;
  }

  ctx.beginPath();
  ctx.moveTo(0, midY);
  ctx.lineTo(ctx.canvas.width, midY);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(midX, 0);
  ctx.lineTo(midX, ctx.canvas.height);
  ctx.stroke();

  drawLabelWithConfidence(label, confidence, ctx, x1, y1);

  if (detection.keypoints) {
    drawKeypoints(ctx, scaleX, scaleY, detection, poseLines, poseKeystrokes);
  }
};

/**
 * Sets up the canvas context for rendering.
 * Adjusts scaling based on the displayed size of the image and applies default styles.
 * @param canvas - The canvas element.
 * @param elem - The HTML element used as a reference for rendering.
 * @returns An object containing the canvas rendering context, scaleX, and scaleY.
 * @example
 * const canvas = document.getElementById("canvas") as HTMLCanvasElement;
 * const elem = document.getElementById("image") as HTMLElement;
 * const { ctx, scaleX, scaleY } = setupCtx(canvas, elem);
 */
export const setupCtx = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  font?: Nullable<string>,
  color?: Nullable<string>,
) => {
  if (!canvas) {
    return {};
  }

  const ctx = canvas!.getContext("2d");

  if (!ctx) {
    return {};
  }

  const isImg = isImage(elem);

  const originalWidth = isImg ? elem.naturalWidth : elem.clientWidth;
  const originalHeight = isImg ? elem.naturalHeight : elem.clientHeight;

  const displayedWidth = elem.clientWidth;
  const displayedHeight = elem.clientHeight;

  const scaleX = displayedWidth / originalWidth;
  const scaleY = displayedHeight / originalHeight;

  canvas.width = displayedWidth;
  canvas.height = displayedHeight;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!font || !color) {
    const styles = getComputedStyle(document.documentElement);
    color = color || styles.getPropertyValue("--color-text").trim();
    font = font || styles.getPropertyValue("--canvas-font").trim();
  }

  ctx.lineWidth = Math.min(
    MAX_LINE_WIDTH,
    Math.max(1, displayedWidth * LINE_WIDTH_SCALING_FACTOR),
  );

  ctx.font = font;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;

  return {
    ctx,
    scaleX,
    scaleY,
  };
};

/**
 * Draws detections on the canvas using the supplied drawing function.
 * @param fn - The function to draw individual detections (e.g., `drawDetectionOverlay` or `drawDetectionCrosshair`).
 * @param canvas - The canvas element.
 * @param elem - The HTML element used as a reference.
 * @param detectionData - An array of detection results.
 * @example
 * drawDetectionsWith(drawDetectionOverlay, canvas, elem, detectionData);
 */
export const drawDetectionsWith = (
  fn: (
    ctx: CanvasRenderingContext2D,
    scaleX: number,
    scaleY: number,
    detection: DetectionResult,
    poseLines?: OverlayLinesParams,
    poseKeystrokes?: KeypointsParams,
    renderFiber?: boolean,
  ) => void,
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  detectionData?: DetectionResult[],
  font?: Nullable<string>,
  color?: Nullable<string>,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
  renderFiber?: boolean,
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, elem, font, color);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection) => {
    fn(ctx, scaleX, scaleY, detection, poseLines, poseKeystrokes, renderFiber);
  });
};
