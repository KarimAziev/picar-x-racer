import {
  drawOverlay,
  drawAimOverlay,
  drawAimMixedOverlay,
  drawKeypointsOnly,
} from "@/features/detection/overlays/overlay";

import { OverlayStyle } from "@/features/detection";

export const overlayStyleHandlers = {
  [OverlayStyle.AIM]: drawAimOverlay,
  [OverlayStyle.BOX]: drawOverlay,
  [OverlayStyle.MIXED]: drawAimMixedOverlay,
  [OverlayStyle.POSE]: drawKeypointsOnly,
};
