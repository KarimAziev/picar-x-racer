import type { DetectionResult } from "@/features/detection";

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
  ctx.fillText(
    `${label.toUpperCase()}: ${(confidence * 100).toFixed(1)}%`,
    x1,
    y1 - 10,
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
) => {
  const { label, confidence, bbox } = detection;
  let [x1, y1, x2, y2] = bbox;

  x1 = x1 * scaleX;
  y1 = y1 * scaleY;
  x2 = x2 * scaleX;
  y2 = y2 * scaleY;

  ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

  drawLabelWithConfidence(label, confidence, ctx, x1, y1);
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
};

/**
 * Sets up the canvas context for rendering.
 * Adjusts scaling based on the displayed size of the image and applies default styles.
 * @param canvas - The canvas element.
 * @param img - The image element used as a reference for rendering.
 * @returns An object containing the canvas rendering context, scaleX, and scaleY.
 * @example
 * const canvas = document.getElementById("canvas") as HTMLCanvasElement;
 * const img = document.getElementById("image") as HTMLImageElement;
 * const { ctx, scaleX, scaleY } = setupCtx(canvas, img);
 */
export const setupCtx = (canvas: HTMLCanvasElement, img: HTMLImageElement) => {
  if (!canvas || !img) {
    return {};
  }

  const ctx = canvas!.getContext("2d");

  if (!ctx) {
    return {};
  }

  const originalWidth = img.naturalWidth;
  const originalHeight = img.naturalHeight;

  const displayedWidth = img.clientWidth;
  const displayedHeight = img.clientHeight;

  const scaleX = displayedWidth / originalWidth;
  const scaleY = displayedHeight / originalHeight;

  canvas.width = displayedWidth;
  canvas.height = displayedHeight;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const styles = getComputedStyle(document.documentElement);
  const color = styles.getPropertyValue("--color-text").trim();
  const font = styles.getPropertyValue("--canvas-font").trim();

  ctx.lineWidth = 4;
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
 * @param img - The image element used as a reference.
 * @param detectionData - An array of detection results.
 * @example
 * drawDetectionsWith(drawDetectionOverlay, canvas, img, detectionData);
 */
export const drawDetectionsWith = (
  fn: (
    ctx: CanvasRenderingContext2D,
    scaleX: number,
    scaleY: number,
    detection: DetectionResult,
  ) => void,
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  detectionData?: DetectionResult[],
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, img);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection) => {
    fn(ctx, scaleX, scaleY, detection);
  });
};

/**
 * Draws overlay annotations on a canvas for the detected objects using bounding boxes and labels.
 * @param canvas - The canvas element.
 * @param img - The image element used as a reference.
 * @param detectionData - An array of detection results.
 * @example
 * drawOverlay(canvas, img, detectionData);
 */
export const drawOverlay = (
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  detectionData?: DetectionResult[],
) => {
  return drawDetectionsWith(drawDetectionOverlay, canvas, img, detectionData);
};

/**
 * Draws crosshair annotations on a canvas for the detected objects.
 * @param canvas - The canvas element.
 * @param img - The image element used as a reference.
 * @param detectionData - An array of detection results.
 * @example
 * drawAimOverlay(canvas, img, detectionData);
 */
export const drawAimOverlay = (
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  detectionData?: DetectionResult[],
) => {
  return drawDetectionsWith(drawDetectionCrosshair, canvas, img, detectionData);
};
