import {
  drawOverlay,
  drawAimOverlay,
  drawAimMixedOverlay,
} from "@/util/overlay";
import { OverlayStyle } from "@/features/detection/store";

export const overlayStyleHandlers = {
  [OverlayStyle.AIM]: drawAimOverlay,
  [OverlayStyle.BOX]: drawOverlay,
  [OverlayStyle.MIXED]: drawAimMixedOverlay,
};
