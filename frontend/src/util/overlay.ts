import type { DetectionResult } from "@/features/detection";

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
  ctx.moveTo(x1, midY);
  ctx.lineTo(x2, midY);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(midX, y1);
  ctx.lineTo(midX, y2);
  ctx.stroke();
  drawLabelWithConfidence(label, confidence, ctx, x1, y1);
};

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

export const drawOverlay = (
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  detectionData?: DetectionResult[],
) => {
  return drawDetectionsWith(drawDetectionOverlay, canvas, img, detectionData);
};

export const drawAimOverlay = (
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  detectionData?: DetectionResult[],
) => {
  return drawDetectionsWith(drawDetectionCrosshair, canvas, img, detectionData);
};
