import type { DetectionResult } from "@/features/detection";
import { where } from "@/util/func";
import { mapObj } from "@/util/obj";
import { getStyleVariable, normalizeThemeName } from "@/util/theme";
import { takePercentage } from "@/util/number";

/**
 * 0: Nose 1: Left Eye 2: Right Eye 3: Left Ear 4: Right Ear 5: Left Shoulder 6:
   Right Shoulder 7: Left Elbow 8: Right Elbow 9: Left Wrist 10: Right Wrist 11:
   Left Hip 12: Right Hip 13: Left Knee 14: Right Knee 15: Left Ankle 16: Right
   Ankle
 */

export enum PARTS {
  NOSE = 0,
  LEFT_EYE = 1,
  RIGHT_EYE = 2,
  LEFT_EAR = 3,
  RIGHT_EAR = 4,
  LEFT_SHOULDER = 5,
  RIGHT_SHOULDER = 6,
  LEFT_ELBOW = 7,
  RIGHT_ELBOW = 8,
  LEFT_WRIST = 9,
  RIGHT_WRIST = 10,
  LEFT_HIP = 11,
  RIGHT_HIP = 12,
  LEFT_KNEE = 13,
  RIGHT_KNEE = 14,
  LEFT_ANKLE = 15,
  RIGHT_ANKLE = 16,
}

const keypointsColors = mapObj(normalizeThemeName, {
  [PARTS.NOSE]: "none", // Nose
  [PARTS.LEFT_EYE]: "red", // Left Eye
  [PARTS.RIGHT_EYE]: "red", // Right Eye
  [PARTS.LEFT_EAR]: "none", // Left Ear
  [PARTS.RIGHT_EAR]: "none", // Right Ear
  [PARTS.LEFT_SHOULDER]: "violet-600", // Left Shoulder
  [PARTS.RIGHT_SHOULDER]: "violet-600", // Right Shoulder
  [PARTS.LEFT_ELBOW]: "violet-600", // Left Elbow
  [PARTS.RIGHT_ELBOW]: "violet-600", // Right Elbow
  [PARTS.LEFT_WRIST]: "violet-600", // Left Wrist
  [PARTS.RIGHT_WRIST]: "violet-600", // Right Wrist
  [PARTS.LEFT_HIP]: "violet-600", // Left Hip
  [PARTS.RIGHT_HIP]: "violet-600", // Right Hip
  [PARTS.LEFT_KNEE]: "violet-600", // Left Knee
  [PARTS.RIGHT_KNEE]: "violet-600", // Right Knee
  [PARTS.LEFT_ANKLE]: "violet-600", // Left Ankle
  [PARTS.RIGHT_ANKLE]: "violet-600", // Right Ankle
});

export type SkeletonItem = [PARTS, PARTS, number, string];

export const normalizeSkeleton = (skeletonItems: SkeletonItem[]) =>
  skeletonItems.map(
    (item) =>
      (item as SkeletonItem)
        .slice(0, -1)
        .concat([normalizeThemeName(item.pop() as string)]) as SkeletonItem,
  );

const SKELETON: SkeletonItem[] = normalizeSkeleton([
  // head
  [PARTS.NOSE, PARTS.LEFT_EYE, 25, "primary-900"], // nose to left eye
  [PARTS.NOSE, PARTS.RIGHT_EYE, 25, "primary-900"], // nose to right eye
  [PARTS.LEFT_EYE, PARTS.LEFT_EAR, 25, "primary-900"], // left eye to left ear
  [PARTS.RIGHT_EYE, PARTS.RIGHT_EAR, 25, "primary-900"], // right eye to right ear
  // arms
  [PARTS.LEFT_SHOULDER, PARTS.LEFT_ELBOW, 70, "fuchsia"], // left shoulder to left elbow
  [PARTS.LEFT_ELBOW, PARTS.LEFT_WRIST, 70, "fuchsia"], // left elbow to left wrist
  [PARTS.RIGHT_SHOULDER, PARTS.RIGHT_ELBOW, 70, "fuchsia"], // right shoulder to right elbow
  [PARTS.RIGHT_ELBOW, PARTS.RIGHT_WRIST, 70, "fuchsia"], // right elbow to right wrist
  // body
  [PARTS.LEFT_SHOULDER, PARTS.RIGHT_SHOULDER, 70, "fuchsia"], // left shoulder to right shoulder
  [PARTS.LEFT_SHOULDER, PARTS.LEFT_HIP, 70, "fuchsia"], // left shoulder to left hip
  [PARTS.RIGHT_SHOULDER, PARTS.RIGHT_HIP, 70, "fuchsia"], // right shoulder to right Hip
  [PARTS.LEFT_HIP, PARTS.RIGHT_HIP, 70, "fuchsia"], // left hip to right hip
  // legs
  [PARTS.LEFT_HIP, PARTS.LEFT_KNEE, 70, "fuchsia"], // left hip to left knee
  [PARTS.LEFT_KNEE, PARTS.LEFT_ANKLE, 70, "fuchsia"], // left knee to left ankle
  [PARTS.RIGHT_HIP, PARTS.RIGHT_KNEE, 70, "fuchsia"], // right hip to right knee
  [PARTS.RIGHT_KNEE, PARTS.RIGHT_ANKLE, 70, "fuchsia"], // right knee to right ankle
]);

const keystrokesPred = where({
  y: (v: number) => v && v >= 0,
});

/**
 * Draws keypoints on the canvas at the specified coordinates.
 * @param ctx - The canvas rendering context.
 * @param scaleX - Horizontal scaling factor for the keypoint coordinates.
 * @param scaleY - Vertical scaling factor for the keypoint coordinates.
 * @param detection - Detection result containing keypoints.
 * @example
 * drawKeypoints(ctx, 1, 1, { keypoints: [{ x: 50, y: 50, conf: 0.9 }, ...] });
 */
export const drawKeypoints = (
  ctx: CanvasRenderingContext2D,
  scaleX: number,
  scaleY: number,
  detection: DetectionResult,
) => {
  if (!detection.keypoints || detection.keypoints.length < 2) {
    return;
  }

  const styles = getComputedStyle(document.documentElement);
  const cachedVars = new Map<string, string | undefined>();
  const getVar = (name: string) => {
    if (cachedVars.has(name)) {
      return cachedVars.get(name) || "";
    }
    const value = getStyleVariable(name, styles);
    cachedVars.set(name, value);
    return value || "";
  };

  const keypoints = detection.keypoints.map(({ x, y }) => ({
    x: x * scaleX,
    y: y * scaleY,
  }));

  const maxLineWidth = ctx.lineWidth;

  const renderGroup = ([startIdx, endIdx, lWidth, colName]: SkeletonItem) => {
    const start = keypoints[startIdx];
    const end = keypoints[endIdx];

    if (keystrokesPred(start) && keystrokesPred(end)) {
      const lineWidth = takePercentage(maxLineWidth, lWidth);

      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.lineWidth = lineWidth * 2;
      ctx.strokeStyle = getVar("--p-primary-500");
      ctx.stroke();

      // the primary line
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      const primaryCol = getVar(colName);
      if (primaryCol) {
        ctx.strokeStyle = primaryCol;
      }
      ctx.lineWidth = lineWidth;
      ctx.stroke();
    }
  };

  const fontSize = parseFloat(ctx.font);

  SKELETON.forEach(renderGroup);

  keypoints.forEach(({ x, y }, i) => {
    const keyColor = getVar(keypointsColors[i as keyof typeof keypointsColors]);

    if (!keyColor) {
      return;
    }
    ctx.beginPath();
    if ([PARTS.RIGHT_EYE, PARTS.LEFT_EYE].includes(i)) {
      ctx.arc(x, y, fontSize / 3, 0, 2 * Math.PI);
      ctx.strokeStyle = keyColor;
      ctx.stroke();
    } else {
      ctx.arc(x, y, fontSize / 4, 0, 2 * Math.PI);
      ctx.fillStyle = keyColor;
      ctx.fill();
    }
  });
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
    drawKeypoints(ctx, scaleX, scaleY, detection);
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

/**
 * Draws crosshair lines (centered) within the bounding box for the detected object of the full canvas width and height.
 * Calls `drawLabelWithConfidence` to display the label and confidence.
 * @param ctx - The canvas rendering context.
 * @param scaleX - Horizontal scaling factor for the bounding box coordinates.
 * @param scaleY - Vertical scaling factor for the bounding box coordinates.
 * @param detection - The detection result containing the label, confidence, and bounding box.
 * @example
 * drawDetectionCrosshair(ctx, 1, 1, { label: "Dog", confidence: 0.92, bbox: [50, 50, 150, 200] });
 */
export const drawFullDetectionCrosshair = (
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
  const scalingFactor = 0.004;
  const maxLineWidth = 4;

  const scaleX = displayedWidth / originalWidth;
  const scaleY = displayedHeight / originalHeight;

  canvas.width = displayedWidth;
  canvas.height = displayedHeight;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const styles = getComputedStyle(document.documentElement);
  const color = styles.getPropertyValue("--color-text").trim();
  const font = styles.getPropertyValue("--canvas-font").trim();

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
  const { ctx, scaleX, scaleY } = setupCtx(canvas, img);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection, i) => {
    const fn = i === 0 ? drawFullDetectionCrosshair : drawDetectionCrosshair;
    fn(ctx, scaleX, scaleY, detection);
  });
};

/**
 * Draws crosshair annotations on a canvas for the detected objects.
 * @param canvas - The canvas element.
 * @param img - The image element used as a reference.
 * @param detectionData - An array of detection results.
 * @example
 * drawAimOverlay(canvas, img, detectionData);
 */
export const drawAimMixedOverlay = (
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  detectionData?: DetectionResult[],
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, img);
  if (!ctx) {
    return;
  }

  detectionData?.forEach((detection, i) => {
    const fn = i === 0 ? drawFullDetectionCrosshair : drawDetectionOverlay;
    fn(ctx, scaleX, scaleY, detection);
  });
};

export const drawKeypointsOnly = (
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  detectionData?: DetectionResult[],
) => {
  const { ctx, scaleX, scaleY } = setupCtx(canvas, img);
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
      drawKeypoints(ctx, scaleX, scaleY, detection);
    }
  });
};
