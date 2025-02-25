import { where } from "@/util/func";
import { BODY_PARTS } from "@/features/detection/enums";
import { getStyleVariable } from "@/util/theme";
import type {
  OverlayParamItem,
  Keypoint,
} from "@/features/detection/interface";

export type SkeletonItem = [BODY_PARTS, BODY_PARTS, number, string];
export type SkeletonLineSpec = [
  BODY_PARTS,
  BODY_PARTS,
  number,
  string,
  boolean,
];

export const keystrokesPred = where({
  y: (v: number) => v && v >= 0,
});

export const isSkeletonFullfilled = (
  detectionKeypoints: { x: number; y: number }[],
) => detectionKeypoints.every(keystrokesPred);

export const mergeSkeleton = (
  skeletonItems: SkeletonItem[],
  params?: OverlayParamItem,
) => {
  let styles: CSSStyleDeclaration;
  let cachedVars: Map<string, string | undefined>;
  const getVar = (name: string) => {
    if (!styles) {
      styles = getComputedStyle(document.documentElement);
    }
    if (!cachedVars) {
      cachedVars = new Map<string, string | undefined>();
    }
    if (cachedVars.has(name)) {
      return cachedVars.get(name) || "";
    }
    const value = getStyleVariable(name, styles);
    cachedVars.set(name, value);
    return value || "";
  };
  return skeletonItems.map(
    ([startIdx, endIdx, lWidth, colName]: SkeletonItem): SkeletonLineSpec => {
      return [
        startIdx,
        endIdx,
        params ? params.size : lWidth,
        params?.color || getVar(colName),
        params?.renderFiber || false,
      ];
    },
  );
};

export const scaleKeypoints = (
  scaleX: number,
  scaleY: number,
  keypoints: Keypoint[],
) =>
  keypoints.map(({ x, y }) => ({
    x: x * scaleX,
    y: y * scaleY,
  }));
