import type { DetectionResult } from "@/features/detection";
import { drawKeypoints } from "@/util/pose";
import { isImage } from "@/util/guards";
import { OverlayLinesParams, KeypointsParams } from "@/types/overlay";

export const defaults = {
  lines: {
    head: { color: "primary-600", size: 25 },
    body: { color: "primary-600", size: 40 },
    arms: { color: "primary-600", size: 40 },
    legs: { color: "primary-600", size: 40 },
  },
  keypoints: {
    eye: { color: "primary-600", size: 40 },
    nose: { color: "primary-600", size: 40 },
    shoulder: { color: "primary-600", size: 40 },
    elbow: { color: "primary-600", size: 40 },
    wrist: { color: "primary-600", size: 40 },
    hip: { color: "primary-600", size: 40 },
    knee: { color: "primary-600", size: 40 },
    ankle: { color: "primary-600", size: 40 },
  },
  fontSizeVar: "--canvas-font",
  colorVar: "--p-primary-500",
};

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
  renderFiber?: boolean,
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
    drawKeypoints(
      ctx,
      scaleX,
      scaleY,
      detection,
      poseLines,
      poseKeystrokes,
      renderFiber,
    );
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
  renderFiber?: boolean,
) => {
  const { label, confidence, bbox, keypoints } = detection;
  let [x1, y1, x2, y2] = bbox;

  x1 = x1 * scaleX;
  y1 = y1 * scaleY;
  x2 = x2 * scaleX;
  y2 = y2 * scaleY;

  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;

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
    drawKeypoints(
      ctx,
      scaleX,
      scaleY,
      detection,
      poseLines,
      poseKeystrokes,
      renderFiber,
    );
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
  renderFiber?: boolean,
) => {
  const { label, confidence, bbox } = detection;
  let [x1, y1, x2, y2] = bbox;

  x1 = x1 * scaleX;
  y1 = y1 * scaleY;
  x2 = x2 * scaleX;
  y2 = y2 * scaleY;

  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;

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
    drawKeypoints(
      ctx,
      scaleX,
      scaleY,
      detection,
      poseLines,
      poseKeystrokes,
      renderFiber,
    );
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
  font?: string,
  color?: string,
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
  const scalingFactor = 0.004;
  const maxLineWidth = 4;

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
    maxLineWidth,
    Math.max(1, displayedWidth * scalingFactor),
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
  font?: string,
  color?: string,
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

/**
 * Draws overlay annotations on a canvas for the detected objects using bounding boxes and labels.
 * @param canvas - The canvas element.
 * @param elem - The HTML element used as a reference.
 * @param detectionData - An array of detection results.
 * @example
 * drawOverlay(canvas, elem, detectionData);
 */
export const drawOverlay = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  detectionData?: DetectionResult[],
  font?: string,
  color?: string,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
  renderFiber?: boolean,
) => {
  return drawDetectionsWith(
    drawDetectionOverlay,
    canvas,
    elem,
    detectionData,
    font,
    color,
    poseLines,
    poseKeystrokes,
    renderFiber,
  );
};

/**
 * Draws crosshair annotations on a canvas for the detected objects.
 * @param canvas - The canvas element.
 * @param elem - The HTML element used as a reference.
 * @param detectionData - An array of detection results.
 * @example
 * drawAimOverlay(canvas, elem, detectionData);
 */
export const drawAimOverlay = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  detectionData?: DetectionResult[],
  font?: string,
  color?: string,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
  renderFiber?: boolean,
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, elem, font, color);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection, i) => {
    const fn = i === 0 ? drawFullDetectionCrosshair : drawDetectionCrosshair;
    fn(ctx, scaleX, scaleY, detection, poseLines, poseKeystrokes, renderFiber);
  });
};

/**
 * Draws crosshair annotations on a canvas for the detected objects.
 * @param canvas - The canvas element.
 * @param elem - The HTML element used as a reference.
 * @param detectionData - An array of detection results.
 * @example
 * drawAimMixedOverlay(canvas, elem, detectionData);
 */
export const drawAimMixedOverlay = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  detectionData?: DetectionResult[],
  font?: string,
  color?: string,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
  renderFiber?: boolean,
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, elem, font, color);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection, i) => {
    const fn = i === 0 ? drawFullDetectionCrosshair : drawDetectionOverlay;
    fn(ctx, scaleX, scaleY, detection, poseLines, poseKeystrokes, renderFiber);
  });
};

export const drawKeypointsOnly = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  detectionData?: DetectionResult[],
  font?: string,
  color?: string,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
  renderFiber?: boolean,
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, elem, font, color);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection) => {
    const { label, confidence, bbox, keypoints } = detection;
    if (bbox) {
      let [x1, y1, x2, y2] = bbox;

      x1 = x1 * scaleX;
      y1 = y1 * scaleY;
      x2 = x2 * scaleX;
      y2 = y2 * scaleY;
      drawLabelWithConfidence(label, confidence, ctx, x1, y1);
    }

    if (keypoints) {
      drawKeypoints(
        ctx,
        scaleX,
        scaleY,
        detection,
        poseLines,
        poseKeystrokes,
        renderFiber,
      );
    }
  });
};
