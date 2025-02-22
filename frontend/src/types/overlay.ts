export interface OverlayParamItem {
  color?: string;
  size: number;
}

export interface OverlayLinesParams {
  head: OverlayParamItem;
  torse: OverlayParamItem;
  arms: OverlayParamItem;
  legs: OverlayParamItem;
}

export interface KeypointsParams {
  eye: OverlayParamItem;
  ear: OverlayParamItem;
  nose: OverlayParamItem;
  shoulder: OverlayParamItem;
  elbow: OverlayParamItem;
  wrist: OverlayParamItem;
  hip: OverlayParamItem;
  knee: OverlayParamItem;
  ankle: OverlayParamItem;
}

export type KeypointGroupProp = keyof KeypointsParams;
