import {
  drawOverlay,
  drawAimOverlay,
  drawAimMixedOverlay,
  drawKeypointsOnly,
  drawSegmentOverlay,
  drawSegmentOnlyOverlay,
  drawSemanticOverlay,
} from "@/features/detection/overlays/overlay";
import type { DetectionOverlayHandler } from "@/features/detection/overlays/overlay";

import { OverlayStyle } from "@/features/detection";

export const overlayStyleHandlers: Record<
  OverlayStyle,
  DetectionOverlayHandler
> = {
  [OverlayStyle.AIM]: drawAimOverlay,
  [OverlayStyle.BOX]: drawOverlay,
  [OverlayStyle.MIXED]: drawAimMixedOverlay,
  [OverlayStyle.POSE]: drawKeypointsOnly,
  [OverlayStyle.BBOX_SEGMENT]: drawSegmentOverlay,
  [OverlayStyle.NO_BBOX_SEGMENT]: drawSegmentOnlyOverlay,
  [OverlayStyle.SEMANTIC]: drawSemanticOverlay,
};
