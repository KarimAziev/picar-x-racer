import { OverlayStyle } from "@/features/detection/enums";

export interface DetectionSettings {
  /**
   * The name or ID of the detection model to be used.
   */
  model: string | null;

  /**
   * The confidence threshold for detections (e.g., a value between 0 and 1).
   */
  confidence: number;

  /**
   * Indicates whether detection is active.
   */
  active: boolean;

  /**
   * The size of the image for detection (default is 640).
   */
  img_size: number;

  /**
   * A list of labels (e.g., object categories) to filter detections.
   */
  labels: string[] | null;
  /**
   * The maximum allowable time difference (in seconds) between the frame
   *  timestamp and the detection timestamp for overlay drawing to occur.
   */
  overlay_draw_threshold: number;
  /**
   * The detection overlay styles
   */
  overlay_style: OverlayStyle;
}

export interface DetectionResponse {
  detection_result: DetectionResult[];
  timestamp: number | null;
  loading: boolean;
}

export type Keypoint = { x: number; y: number };

export interface DetectionResult {
  bbox: [number, number, number, number];
  label: string;
  confidence: number;
  keypoints?: Keypoint[];
}

export interface ItemConfig {
  color?: string;
  size: number;
}

export interface OverlayParamItem extends ItemConfig {
  renderFiber?: boolean;
}

export interface OverlayLinesParams {
  head: OverlayParamItem;
  torso: OverlayParamItem;
  arms: OverlayParamItem;
  legs: OverlayParamItem;
}

export interface KeypointsParams {
  eye: ItemConfig;
  ear: ItemConfig;
  nose: ItemConfig;
  shoulder: ItemConfig;
  elbow: ItemConfig;
  wrist: ItemConfig;
  hip: ItemConfig;
  knee: ItemConfig;
  ankle: ItemConfig;
}

export type KeypointGroupProp = keyof KeypointsParams;
