import {
  DetectionResult,
  OverlayLinesParams,
  KeypointsParams,
} from "@/features/detection/interface";
import {
  setupCtx,
  drawDetectionsWith,
  drawDetectionOverlay,
  drawFullDetectionCrosshair,
  drawDetectionCrosshair,
  drawLabelWithConfidence,
} from "@/features/detection/overlays/util";
import { drawKeypoints } from "@/features/detection/overlays/pose/canvasPoseRenderer";
import { Nullable } from "@/util/ts-helpers";

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
  font?: Nullable<string>,
  color?: Nullable<string>,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
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
  font?: Nullable<string>,
  color?: Nullable<string>,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, elem, font, color);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection, i) => {
    const fn = i === 0 ? drawFullDetectionCrosshair : drawDetectionCrosshair;
    fn(ctx, scaleX, scaleY, detection, poseLines, poseKeystrokes);
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
  font?: Nullable<string>,
  color?: Nullable<string>,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, elem, font, color);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection, i) => {
    const fn = i === 0 ? drawFullDetectionCrosshair : drawDetectionOverlay;
    fn(ctx, scaleX, scaleY, detection, poseLines, poseKeystrokes);
  });
};

export const drawKeypointsOnly = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  detectionData?: DetectionResult[],
  font?: Nullable<string>,
  color?: Nullable<string>,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
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
      drawKeypoints(ctx, scaleX, scaleY, detection, poseLines, poseKeystrokes);
    }
  });
};
