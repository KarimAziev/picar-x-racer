import { BODY_PARTS } from "@/features/detection/enums";
import {
  KeypointGroupProp,
  OverlayLinesParams,
} from "@/features/detection/interface";
import { normalizeThemeName } from "@/util/theme";
import { mapObj } from "@/util/obj";

/**
 * 0: Nose 1: Left Eye 2: Right Eye 3: Left Ear 4: Right Ear 5: Left Shoulder 6:
   Right Shoulder 7: Left Elbow 8: Right Elbow 9: Left Wrist 10: Right Wrist 11:
   Left Hip 12: Right Hip 13: Left Knee 14: Right Knee 15: Left Ankle 16: Right
   Ankle
 */

export const keypointsGroups: Record<BODY_PARTS, KeypointGroupProp> = {
  [BODY_PARTS.NOSE]: "nose", // Nose
  [BODY_PARTS.LEFT_EYE]: "eye", // Left Eye
  [BODY_PARTS.RIGHT_EYE]: "eye", // Right Eye
  [BODY_PARTS.LEFT_EAR]: "ear", // Left Ear
  [BODY_PARTS.RIGHT_EAR]: "ear", // Right Ear
  [BODY_PARTS.LEFT_SHOULDER]: "shoulder", // Left Shoulder
  [BODY_PARTS.RIGHT_SHOULDER]: "shoulder", // Right Shoulder
  [BODY_PARTS.LEFT_ELBOW]: "elbow", // Left Elbow
  [BODY_PARTS.RIGHT_ELBOW]: "elbow", // Right Elbow
  [BODY_PARTS.LEFT_WRIST]: "wrist", // Left Wrist
  [BODY_PARTS.RIGHT_WRIST]: "wrist", // Right Wrist
  [BODY_PARTS.LEFT_HIP]: "hip", // Left Hip
  [BODY_PARTS.RIGHT_HIP]: "hip", // Right Hip
  [BODY_PARTS.LEFT_KNEE]: "knee", // Left Knee
  [BODY_PARTS.RIGHT_KNEE]: "knee", // Right Knee
  [BODY_PARTS.LEFT_ANKLE]: "ankle", // Left Ankle
  [BODY_PARTS.RIGHT_ANKLE]: "ankle", // Right Ankle
};

export const HEADBONE_BODY_PARTS = [
  BODY_PARTS.NOSE,
  BODY_PARTS.LEFT_EYE,
  BODY_PARTS.RIGHT_EYE,
  BODY_PARTS.LEFT_EAR,
  BODY_PARTS.RIGHT_EAR,
].reduce(
  (acc, val) => ({ ...acc, [val]: true }),
  {} as Partial<{ [K in BODY_PARTS]: boolean }>,
);

export const headColor = normalizeThemeName("primary-600");
export const bodyColor = normalizeThemeName("primary-800");
export const armsColor = normalizeThemeName("primary-700");
export const legsColor = normalizeThemeName("primary-700");
export const keypointEyeColor = normalizeThemeName("primary-100");
export const keypointShoulderColor = normalizeThemeName("primary-900");
export const keypointElbowColor = normalizeThemeName("primary-900");
export const keypointWristColor = normalizeThemeName("primary-900");
export const keypointHipColor = normalizeThemeName("primary-900");
export const keypointKneeColor = normalizeThemeName("primary-900");
export const keypointAnkleColor = normalizeThemeName("primary-900");

export const keypointsColors = mapObj(normalizeThemeName, {
  [BODY_PARTS.NOSE]: "none", // Nose
  [BODY_PARTS.LEFT_EYE]: keypointEyeColor, // Left Eye
  [BODY_PARTS.RIGHT_EYE]: keypointEyeColor, // Right Eye
  [BODY_PARTS.LEFT_EAR]: "none", // Left Ear
  [BODY_PARTS.RIGHT_EAR]: "none", // Right Ear
  [BODY_PARTS.LEFT_SHOULDER]: keypointShoulderColor, // Left Shoulder
  [BODY_PARTS.RIGHT_SHOULDER]: keypointShoulderColor, // Right Shoulder
  [BODY_PARTS.LEFT_ELBOW]: keypointElbowColor, // Left Elbow
  [BODY_PARTS.RIGHT_ELBOW]: keypointElbowColor, // Right Elbow
  [BODY_PARTS.LEFT_WRIST]: keypointWristColor, // Left Wrist
  [BODY_PARTS.RIGHT_WRIST]: keypointWristColor, // Right Wrist
  [BODY_PARTS.LEFT_HIP]: keypointHipColor, // Left Hip
  [BODY_PARTS.RIGHT_HIP]: keypointHipColor, // Right Hip
  [BODY_PARTS.LEFT_KNEE]: keypointKneeColor, // Left Knee
  [BODY_PARTS.RIGHT_KNEE]: keypointKneeColor, // Right Knee
  [BODY_PARTS.LEFT_ANKLE]: keypointAnkleColor, // Left Ankle
  [BODY_PARTS.RIGHT_ANKLE]: keypointAnkleColor, // Right Ankle
});
export type SkeletonItem = [BODY_PARTS, BODY_PARTS, number, string];
export const HEAD_SKELETON: SkeletonItem[] = [
  [BODY_PARTS.NOSE, BODY_PARTS.LEFT_EYE, 25, headColor], // nose to left eye
  [BODY_PARTS.NOSE, BODY_PARTS.RIGHT_EYE, 25, headColor], // nose to right eye
  [BODY_PARTS.LEFT_EYE, BODY_PARTS.LEFT_EAR, 25, headColor], // left eye to left ear
  [BODY_PARTS.RIGHT_EYE, BODY_PARTS.RIGHT_EAR, 25, headColor], // right eye to right ear
] as const;

export const UPPER_ARMS_SKELETON: SkeletonItem[] = [
  [BODY_PARTS.LEFT_SHOULDER, BODY_PARTS.LEFT_ELBOW, 40, armsColor], // left shoulder to left elbow
  [BODY_PARTS.RIGHT_SHOULDER, BODY_PARTS.RIGHT_ELBOW, 40, armsColor], // right shoulder to right elbow
] as const;

export const LOWER_ARMS_SKELETON: SkeletonItem[] = [
  [BODY_PARTS.LEFT_ELBOW, BODY_PARTS.LEFT_WRIST, 40, armsColor], // left elbow to left wrist
  [BODY_PARTS.RIGHT_ELBOW, BODY_PARTS.RIGHT_WRIST, 40, armsColor], // right elbow to right wrist
] as const;

export const BODY_SKELETON: SkeletonItem[] = [
  [BODY_PARTS.LEFT_SHOULDER, BODY_PARTS.RIGHT_SHOULDER, 40, bodyColor], // left shoulder to right shoulder
  [BODY_PARTS.LEFT_SHOULDER, BODY_PARTS.LEFT_HIP, 40, bodyColor], // left shoulder to left hip
  [BODY_PARTS.RIGHT_SHOULDER, BODY_PARTS.RIGHT_HIP, 40, bodyColor], // right shoulder to right Hip
  [BODY_PARTS.LEFT_HIP, BODY_PARTS.RIGHT_HIP, 40, bodyColor], // left hip to right hip
] as const;

export const LOWER_LEGS_SKELETON: SkeletonItem[] = [
  [BODY_PARTS.LEFT_KNEE, BODY_PARTS.LEFT_ANKLE, 40, legsColor], // left knee to left ankle
  [BODY_PARTS.RIGHT_KNEE, BODY_PARTS.RIGHT_ANKLE, 40, legsColor], // right knee to right ankle
] as const;

export const THIGH_LEGS_SKELETON: SkeletonItem[] = [
  [BODY_PARTS.LEFT_HIP, BODY_PARTS.LEFT_KNEE, 40, legsColor],
  [BODY_PARTS.RIGHT_HIP, BODY_PARTS.RIGHT_KNEE, 40, legsColor],
] as const;

export const overlayLinesGrouped: {
  [P in keyof OverlayLinesParams]: SkeletonItem[];
} = {
  head: HEAD_SKELETON,
  torso: BODY_SKELETON,
  upper_arm: UPPER_ARMS_SKELETON,
  lower_arm: LOWER_ARMS_SKELETON,
  thigh: THIGH_LEGS_SKELETON,
  lower_leg: LOWER_LEGS_SKELETON,
};
