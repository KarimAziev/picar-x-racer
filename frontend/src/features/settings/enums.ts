export enum SettingsTab {
  GENERAL = "General",
  KEYBINDINGS = "Keybindings",
  CALIBRATION = "Calibration",
}

export enum VideoFeedURL {
  extra_low_quality_mode = "/mjpg-xlq",
  low_quality_mode = "/mjpg-lq",
  low_quality_png_mode = "/mpng-lq",
  medium_quality_mode = "/mjpg-mq",
  high_quality_mode = "/mjpg-hq",
  robocop_vision_mode = "/mjpg-xhq",
  cat_recognize_mode = "/mjpg-hq/cat-recognize",
  cat_recognize_extended_mode = "/mjpg-hq/cat-recognize-extended",
  human_recognize_mode = "/mjpg-hq/human-face-recognize",
  human_body_recognize_mode = "/mjpg-hq/human-body-recognize",
}

export const videoFeedEntities = Object.entries(VideoFeedURL);
