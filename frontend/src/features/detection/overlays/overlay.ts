import {
  DetectionResult,
  OverlayLinesParams,
  KeypointsParams,
  SemanticMaskData,
} from "@/features/detection/interface";
import {
  setupCtx,
  drawDetectionsWith,
  drawDetectionOverlay,
  drawDetectionSegment,
  drawDetectionSegmentOnly,
  drawSemanticMask,
  drawFullDetectionCrosshair,
  drawDetectionCrosshair,
  drawLabelWithConfidence,
} from "@/features/detection/overlays/util";
import { drawKeypoints } from "@/features/detection/overlays/pose/canvasPoseRenderer";
import { Nullable } from "@/util/ts-helpers";

export type DetectionOverlayHandler = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  detectionData?: DetectionResult[],
  font?: Nullable<string>,
  color?: Nullable<string>,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
  semanticMask?: SemanticMaskData | null,
  keypointConfidenceThreshold?: number,
) => void;

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
  _semanticMask?: SemanticMaskData | null,
  keypointConfidenceThreshold?: number,
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
    keypointConfidenceThreshold,
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
  _semanticMask?: SemanticMaskData | null,
  keypointConfidenceThreshold?: number,
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, elem, font, color);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection, i) => {
    const fn = i === 0 ? drawFullDetectionCrosshair : drawDetectionCrosshair;
    fn(
      ctx,
      scaleX,
      scaleY,
      detection,
      poseLines,
      poseKeystrokes,
      keypointConfidenceThreshold,
    );
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
  _semanticMask?: SemanticMaskData | null,
  keypointConfidenceThreshold?: number,
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, elem, font, color);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection, i) => {
    const fn = i === 0 ? drawFullDetectionCrosshair : drawDetectionOverlay;
    fn(
      ctx,
      scaleX,
      scaleY,
      detection,
      poseLines,
      poseKeystrokes,
      keypointConfidenceThreshold,
    );
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
  _semanticMask?: SemanticMaskData | null,
  keypointConfidenceThreshold?: number,
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
        keypointConfidenceThreshold,
      );
    }
  });
};

export const drawSegmentOverlay = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  detectionData?: DetectionResult[],
  font?: Nullable<string>,
  color?: Nullable<string>,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
  _semanticMask?: SemanticMaskData | null,
  keypointConfidenceThreshold?: number,
) => {
  return drawDetectionsWith(
    drawDetectionSegment,
    canvas,
    elem,
    detectionData,
    font,
    color,
    poseLines,
    poseKeystrokes,
    keypointConfidenceThreshold,
  );
};

export const drawSegmentOnlyOverlay = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  detectionData?: DetectionResult[],
  font?: Nullable<string>,
  color?: Nullable<string>,
  poseLines?: OverlayLinesParams,
  poseKeystrokes?: KeypointsParams,
  _semanticMask?: SemanticMaskData | null,
  keypointConfidenceThreshold?: number,
) => {
  return drawDetectionsWith(
    drawDetectionSegmentOnly,
    canvas,
    elem,
    detectionData,
    font,
    color,
    poseLines,
    poseKeystrokes,
    keypointConfidenceThreshold,
  );
};

export const drawSemanticOverlay = (
  canvas: HTMLCanvasElement,
  elem: HTMLElement,
  _detectionData?: DetectionResult[],
  font?: Nullable<string>,
  color?: Nullable<string>,
  _poseLines?: OverlayLinesParams,
  _poseKeystrokes?: KeypointsParams,
  semanticMask?: SemanticMaskData | null,
) => {
  const { ctx } = setupCtx(canvas, elem, font, color);
  if (!ctx) {
    return;
  }

  drawSemanticMask(ctx, semanticMask);
};
