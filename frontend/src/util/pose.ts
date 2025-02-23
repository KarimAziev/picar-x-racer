import type { DetectionResult } from "@/features/detection";
import { where } from "@/util/func";
import { mapObj } from "@/util/obj";
import { getStyleVariable, normalizeThemeName } from "@/util/theme";
import { takePercentage } from "@/util/number";
import {
  OverlayParamItem,
  OverlayLinesParams,
  KeypointsParams,
  KeypointGroupProp,
} from "@/types/overlay";

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

const headColor = "primary-600";
const bodyColor = "primary-800";
const armsColor = "primary-700";
const legsColor = "primary-700";
const keypointEyeColor = "primary-100";
const keypointShoulderColor = "primary-900";
const keypointElbowColor = "primary-900";
const keypointWristColor = "primary-900";
const keypointHipColor = "primary-900";
const keypointKneeColor = "primary-900";
const keypointAnkleColor = "primary-900";

const keypointsColors = mapObj(normalizeThemeName, {
  [PARTS.NOSE]: "none", // Nose
  [PARTS.LEFT_EYE]: keypointEyeColor, // Left Eye
  [PARTS.RIGHT_EYE]: keypointEyeColor, // Right Eye
  [PARTS.LEFT_EAR]: "none", // Left Ear
  [PARTS.RIGHT_EAR]: "none", // Right Ear
  [PARTS.LEFT_SHOULDER]: keypointShoulderColor, // Left Shoulder
  [PARTS.RIGHT_SHOULDER]: keypointShoulderColor, // Right Shoulder
  [PARTS.LEFT_ELBOW]: keypointElbowColor, // Left Elbow
  [PARTS.RIGHT_ELBOW]: keypointElbowColor, // Right Elbow
  [PARTS.LEFT_WRIST]: keypointWristColor, // Left Wrist
  [PARTS.RIGHT_WRIST]: keypointWristColor, // Right Wrist
  [PARTS.LEFT_HIP]: keypointHipColor, // Left Hip
  [PARTS.RIGHT_HIP]: keypointHipColor, // Right Hip
  [PARTS.LEFT_KNEE]: keypointKneeColor, // Left Knee
  [PARTS.RIGHT_KNEE]: keypointKneeColor, // Right Knee
  [PARTS.LEFT_ANKLE]: keypointAnkleColor, // Left Ankle
  [PARTS.RIGHT_ANKLE]: keypointAnkleColor, // Right Ankle
});

export type SkeletonItem = [PARTS, PARTS, number, string];

export const normalizeSkeleton = (skeletonItems: SkeletonItem[]) =>
  skeletonItems.map(
    (item) =>
      (item as SkeletonItem)
        .slice(0, -1)
        .concat([normalizeThemeName(item.pop() as string)]) as SkeletonItem,
  );

const HEAD_SKELETON = normalizeSkeleton([
  [PARTS.NOSE, PARTS.LEFT_EYE, 25, headColor], // nose to left eye
  [PARTS.NOSE, PARTS.RIGHT_EYE, 25, headColor], // nose to right eye
  [PARTS.LEFT_EYE, PARTS.LEFT_EAR, 25, headColor], // left eye to left ear
  [PARTS.RIGHT_EYE, PARTS.RIGHT_EAR, 25, headColor], // right eye to right ear
]);
const ARMS_SKELETON = normalizeSkeleton([
  [PARTS.LEFT_SHOULDER, PARTS.LEFT_ELBOW, 40, armsColor], // left shoulder to left elbow
  [PARTS.LEFT_ELBOW, PARTS.LEFT_WRIST, 40, armsColor], // left elbow to left wrist
  [PARTS.RIGHT_SHOULDER, PARTS.RIGHT_ELBOW, 40, armsColor], // right shoulder to right elbow
  [PARTS.RIGHT_ELBOW, PARTS.RIGHT_WRIST, 40, armsColor], // right elbow to right wrist
]);

const BODY_SKELETON = normalizeSkeleton([
  [PARTS.LEFT_SHOULDER, PARTS.RIGHT_SHOULDER, 40, bodyColor], // left shoulder to right shoulder
  [PARTS.LEFT_SHOULDER, PARTS.LEFT_HIP, 40, bodyColor], // left shoulder to left hip
  [PARTS.RIGHT_SHOULDER, PARTS.RIGHT_HIP, 40, bodyColor], // right shoulder to right Hip
  [PARTS.LEFT_HIP, PARTS.RIGHT_HIP, 40, bodyColor], // left hip to right hip
]);

const LEGS_SKELETON = normalizeSkeleton([
  [PARTS.LEFT_HIP, PARTS.LEFT_KNEE, 40, legsColor], // left hip to left knee
  [PARTS.LEFT_KNEE, PARTS.LEFT_ANKLE, 40, legsColor], // left knee to left ankle
  [PARTS.RIGHT_HIP, PARTS.RIGHT_KNEE, 40, legsColor], // right hip to right knee
  [PARTS.RIGHT_KNEE, PARTS.RIGHT_ANKLE, 40, legsColor], // right knee to right ankle
]);

export const keypointsGroups: Record<PARTS, KeypointGroupProp> = {
  [PARTS.NOSE]: "nose", // Nose
  [PARTS.LEFT_EYE]: "eye", // Left Eye
  [PARTS.RIGHT_EYE]: "eye", // Right Eye
  [PARTS.LEFT_EAR]: "ear", // Left Ear
  [PARTS.RIGHT_EAR]: "ear", // Right Ear
  [PARTS.LEFT_SHOULDER]: "shoulder", // Left Shoulder
  [PARTS.RIGHT_SHOULDER]: "shoulder", // Right Shoulder
  [PARTS.LEFT_ELBOW]: "elbow", // Left Elbow
  [PARTS.RIGHT_ELBOW]: "elbow", // Right Elbow
  [PARTS.LEFT_WRIST]: "wrist", // Left Wrist
  [PARTS.RIGHT_WRIST]: "wrist", // Right Wrist
  [PARTS.LEFT_HIP]: "hip", // Left Hip
  [PARTS.RIGHT_HIP]: "hip", // Right Hip
  [PARTS.LEFT_KNEE]: "knee", // Left Knee
  [PARTS.RIGHT_KNEE]: "knee", // Right Knee
  [PARTS.LEFT_ANKLE]: "ankle", // Left Ankle
  [PARTS.RIGHT_ANKLE]: "ankle", // Right Ankle
};
const keystrokesPred = where({
  y: (v: number) => v && v >= 0,
});

export const isSkeletonFullfilled = (
  detectionKeypoints: { x: number; y: number }[],
) => detectionKeypoints.every(keystrokesPred);

export const drawKeypoints = (
  ctx: CanvasRenderingContext2D,
  scaleX: number,
  scaleY: number,
  detection: Pick<DetectionResult, "keypoints">,
  linesParams?: OverlayLinesParams,
  keypointsParams?: KeypointsParams,
  renderFiber?: boolean,
) => {
  if (!detection.keypoints || detection.keypoints.length < 2) {
    return;
  }

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

  const mergeSkeleton = (
    skeletonItems: SkeletonItem[],
    params?: OverlayParamItem,
  ) =>
    skeletonItems.map(
      ([startIdx, endIdx, lWidth, colName]: SkeletonItem): SkeletonItem => [
        startIdx,
        endIdx,
        params ? params.size : lWidth,
        params?.color || getVar(colName),
      ],
    );

  const keypoints = detection.keypoints.map(({ x, y }) => ({
    x: x * scaleX,
    y: y * scaleY,
  }));

  const maxLineWidth = ctx.lineWidth;

  const renderGroup = ([startIdx, endIdx, lWidth, colName]: SkeletonItem) => {
    const start = keypoints[startIdx];
    const end = keypoints[endIdx];
    const curveColor = colName;

    if (!keystrokesPred(start) || !keystrokesPred(end)) {
      return;
    }

    const lineWidth = takePercentage(maxLineWidth, lWidth);

    const headboneParts = [
      PARTS.NOSE,
      PARTS.LEFT_EYE,
      PARTS.RIGHT_EYE,
      PARTS.LEFT_EAR,
      PARTS.RIGHT_EAR,
    ];
    const isHeadBone =
      headboneParts.includes(startIdx) && headboneParts.includes(endIdx);

    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.lineWidth = lineWidth;
    ctx.strokeStyle = colName;
    ctx.stroke();

    if (!isHeadBone && renderFiber) {
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
      ctx.lineWidth = lineWidth * 2.5;
      ctx.strokeStyle = curveColor;
      ctx.stroke();

      // Outer negative curve.
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.quadraticCurveTo(cpOuterNeg.x, cpOuterNeg.y, end.x, end.y);
      ctx.lineWidth = lineWidth * 2.5;
      ctx.strokeStyle = curveColor;
      ctx.stroke();

      // Inner positive curve.
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.quadraticCurveTo(cpInnerPos.x, cpInnerPos.y, end.x, end.y);
      ctx.lineWidth = lineWidth * 1.5;
      ctx.strokeStyle = curveColor;
      ctx.stroke();

      // Inner negative curve.
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.quadraticCurveTo(cpInnerNeg.x, cpInnerNeg.y, end.x, end.y);
      ctx.lineWidth = lineWidth * 1.5;
      ctx.strokeStyle = curveColor;
      ctx.stroke();
    }
  };

  [
    ...mergeSkeleton(HEAD_SKELETON, linesParams?.head),
    ...mergeSkeleton(ARMS_SKELETON, linesParams?.arms),
    ...mergeSkeleton(BODY_SKELETON, linesParams?.torso),
    ...mergeSkeleton(LEGS_SKELETON, linesParams?.legs),
  ].forEach(renderGroup);

  const leftShoulder = keypoints[PARTS.LEFT_SHOULDER];
  const rightShoulder = keypoints[PARTS.RIGHT_SHOULDER];
  const leftHip = keypoints[PARTS.LEFT_HIP];
  const rightHip = keypoints[PARTS.RIGHT_HIP];

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

    const spineColor =
      linesParams?.torso?.color || getVar(normalizeThemeName(bodyColor));
    const spineLineWidth = takePercentage(
      maxLineWidth,
      linesParams?.torso.size || 40,
    );
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

  keypoints.forEach(({ x, y }, i) => {
    const keyPointProp = keypointsGroups[i as PARTS];
    const size = (keypointsParams && keypointsParams[keyPointProp].size) || 25;
    const keyColor =
      (keypointsParams && keypointsParams[keyPointProp].color) ||
      getVar(keypointsColors[i as keyof typeof keypointsColors]);

    if (!keyColor) {
      return;
    }

    ctx.beginPath();

    if ([PARTS.RIGHT_EYE, PARTS.LEFT_EYE].includes(i)) {
      ctx.arc(x, y, takePercentage(fontSize, size), 0, 2 * Math.PI);
      ctx.strokeStyle = keyColor;
      ctx.stroke();
    } else {
      {
        ctx.arc(x, y, takePercentage(fontSize, size), 0, 2 * Math.PI);
        ctx.fillStyle = keyColor;
        ctx.fill();
      }
    }
  });
};
