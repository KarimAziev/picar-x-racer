import type { DetectionResult } from "@/features/detection";
import { getStyleVariable } from "@/util/theme";
import { takePercentage } from "@/util/number";
import type {
  OverlayLinesParams,
  KeypointsParams,
  Keypoint,
} from "@/features/detection/interface";
import {
  keypointsGroups,
  keypointsColors,
  overlayLinesGrouped,
} from "@/features/detection/overlays/pose/config";

import {
  keystrokesPred,
  SkeletonLineSpec,
  scaleKeypoints,
  mergeSkeletonLines,
} from "@/features/detection/overlays/pose/util";
import { BODY_PARTS } from "@/features/detection/enums";

export const drawKeypoints = (
  ctx: CanvasRenderingContext2D,
  scaleX: number,
  scaleY: number,
  detection: Pick<DetectionResult, "keypoints">,
  linesParams?: OverlayLinesParams,
  keypointsParams?: KeypointsParams,
) => {
  if (!detection.keypoints || detection.keypoints.length < 2) {
    return;
  }

  const keypoints = scaleKeypoints(scaleX, scaleY, detection.keypoints);
  const maxLineWidth = ctx.lineWidth;

  const styles = getComputedStyle(document.documentElement);
  const fontSize = parseFloat(ctx.font);

  const cachedVars = new Map<string, string | undefined>();

  const getVar = (name: string) => {
    if (cachedVars.has(name)) {
      return cachedVars.get(name) || "";
    }
    const value = getStyleVariable(name, styles);
    cachedVars.set(name, value);
    return value || "";
  };

  mergeSkeletonLines(overlayLinesGrouped, linesParams).forEach((item) => {
    renderMeshLine(ctx, keypoints, item, maxLineWidth);
  });

  keypoints.forEach((item, i) => {
    drawKeypointCircle(ctx, item, i, fontSize, getVar, keypointsParams);
  });
};

export const renderMeshLine = (
  ctx: CanvasRenderingContext2D,
  keypoints: Keypoint[],
  [startIdx, endIdx, lWidth, colName, renderFiber]: SkeletonLineSpec,
  maxLineWidth: number,
) => {
  const start = keypoints[startIdx];
  const end = keypoints[endIdx];

  if (!keystrokesPred(start) || !keystrokesPred(end)) {
    return;
  }

  const lineWidth = takePercentage(maxLineWidth, lWidth);

  ctx.beginPath();
  ctx.moveTo(start.x, start.y);
  ctx.lineTo(end.x, end.y);
  ctx.lineWidth = lineWidth;
  ctx.strokeStyle = colName;
  ctx.stroke();

  if (renderFiber) {
    drawFiberLine(ctx, start, end, colName, lineWidth);
  }
};

export const drawKeypointCircle = (
  ctx: CanvasRenderingContext2D,
  keypoint: Keypoint,
  idx: number,
  fontSize: number,
  getVar: (name: string) => string,
  keypointsParams?: KeypointsParams,
) => {
  const keyPointProp = keypointsGroups[idx as BODY_PARTS];
  const size = (keypointsParams && keypointsParams[keyPointProp].size) || 25;
  const keyColor =
    (keypointsParams && keypointsParams[keyPointProp].color) ||
    getVar(keypointsColors[idx as keyof typeof keypointsColors]);

  if (!keyColor) {
    return;
  }

  ctx.beginPath();
  ctx.arc(
    keypoint.x,
    keypoint.y,
    takePercentage(fontSize, size),
    0,
    2 * Math.PI,
  );

  if (keyPointProp === "eye") {
    ctx.strokeStyle = keyColor;
    ctx.stroke();
  } else {
    ctx.fillStyle = keyColor;
    ctx.fill();
  }
};

export const drawFiberLine = (
  ctx: CanvasRenderingContext2D,
  start: Keypoint,
  end: Keypoint,
  curveColor: string,
  lineWidth: number,
) => {
  const midX = (start.x + end.x) / 2;
  const midY = (start.y + end.y) / 2;

  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const distance = Math.sqrt(dx * dx + dy * dy);

  let normalX = 0;
  let normalY = 0;
  if (distance !== 0) {
    normalX = -dy / distance;
    normalY = dx / distance;
  }

  const baseOffset = distance * 0.1;

  const cpOuterPos = {
    x: midX + normalX * baseOffset,
    y: midY + normalY * baseOffset,
  };
  const cpOuterNeg = {
    x: midX - normalX * baseOffset,
    y: midY - normalY * baseOffset,
  };
  const cpInnerPos = {
    x: midX + normalX * (baseOffset * 0.5),
    y: midY + normalY * (baseOffset * 0.5),
  };
  const cpInnerNeg = {
    x: midX - normalX * (baseOffset * 0.5),
    y: midY - normalY * (baseOffset * 0.5),
  };

  // For a 3D muscle fiber effect we draw four curves in addition to the main line.

  // Outer positive curve.
  ctx.beginPath();
  ctx.moveTo(start.x, start.y);
  ctx.quadraticCurveTo(cpOuterPos.x, cpOuterPos.y, end.x, end.y);
  ctx.lineWidth = lineWidth * 1.5;
  ctx.strokeStyle = curveColor;
  ctx.stroke();

  // Outer negative curve.
  ctx.beginPath();
  ctx.moveTo(start.x, start.y);
  ctx.quadraticCurveTo(cpOuterNeg.x, cpOuterNeg.y, end.x, end.y);
  ctx.lineWidth = lineWidth * 1.5;
  ctx.strokeStyle = curveColor;
  ctx.stroke();

  // Inner positive curve.
  ctx.beginPath();
  ctx.moveTo(start.x, start.y);
  ctx.quadraticCurveTo(cpInnerPos.x, cpInnerPos.y, end.x, end.y);
  ctx.lineWidth = lineWidth * 0.8;
  ctx.strokeStyle = curveColor;
  ctx.stroke();

  // Inner negative curve.
  ctx.beginPath();
  ctx.moveTo(start.x, start.y);
  ctx.quadraticCurveTo(cpInnerNeg.x, cpInnerNeg.y, end.x, end.y);
  ctx.lineWidth = lineWidth * 0.8;
  ctx.strokeStyle = curveColor;
  ctx.stroke();
};

export const drawSpine = (
  ctx: CanvasRenderingContext2D,
  keypoints: Keypoint[],
  spineColor: string,
  spineLineWidth: number,
  renderFiber?: boolean,
) => {
  const leftShoulder = keypoints[BODY_PARTS.LEFT_SHOULDER];
  const rightShoulder = keypoints[BODY_PARTS.RIGHT_SHOULDER];
  const leftHip = keypoints[BODY_PARTS.LEFT_HIP];
  const rightHip = keypoints[BODY_PARTS.RIGHT_HIP];
  if (
    keystrokesPred(leftShoulder) &&
    keystrokesPred(rightShoulder) &&
    keystrokesPred(leftHip) &&
    keystrokesPred(rightHip)
  ) {
    const spineTop = {
      x: (leftShoulder.x + rightShoulder.x) / 2,
      y: (leftShoulder.y + rightShoulder.y) / 2,
    };
    const spineBottom = {
      x: (leftHip.x + rightHip.x) / 2,
      y: (leftHip.y + rightHip.y) / 2,
    };

    ctx.beginPath();
    ctx.moveTo(spineTop.x, spineTop.y);
    ctx.lineTo(spineBottom.x, spineBottom.y);
    ctx.lineWidth = spineLineWidth;
    ctx.strokeStyle = spineColor;
    ctx.stroke();

    if (renderFiber) {
      const midY = (spineTop.y + spineBottom.y) / 2;

      const ribOffset = 60;

      ctx.beginPath();
      ctx.moveTo(spineTop.x, spineTop.y);

      ctx.quadraticCurveTo(
        spineTop.x - ribOffset,
        midY,
        spineBottom.x,
        spineBottom.y,
      );
      ctx.lineWidth = spineLineWidth * 1.5;
      ctx.strokeStyle = spineColor;
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(spineTop.x, spineTop.y);

      ctx.quadraticCurveTo(
        spineTop.x + ribOffset,
        midY,
        spineBottom.x,
        spineBottom.y,
      );
      ctx.lineWidth = spineLineWidth * 1.5;
      ctx.strokeStyle = spineColor;
      ctx.stroke();
    }
  }
};
