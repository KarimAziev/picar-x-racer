import {
  drawOverlay,
  drawAimOverlay,
  drawAimMixedOverlay,
  drawKeypointsOnly,
  drawSegmentOverlay,
  drawSegmentOnlyOverlay,
} from "@/features/detection/overlays/overlay";

import { OverlayStyle } from "@/features/detection";

export const overlayStyleHandlers = {
  [OverlayStyle.AIM]: drawAimOverlay,
  [OverlayStyle.BOX]: drawOverlay,
  [OverlayStyle.MIXED]: drawAimMixedOverlay,
  [OverlayStyle.POSE]: drawKeypointsOnly,
  [OverlayStyle.BBOX_SEGMENT]: drawSegmentOverlay,
  [OverlayStyle.NO_BBOX_SEGMENT]: drawSegmentOnlyOverlay,
};
