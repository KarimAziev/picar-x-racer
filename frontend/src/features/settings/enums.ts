export enum SettingsTab {
  GENERAL = "General",
  KEYBINDINGS = "Keybindings",
  CALIBRATION = "Calibration",
}

export enum VideoFeedURL {
  high_quality_mode = "/mjpg-hq",
  medium_quality_mode = "/mjpg-mq",
  low_quality_mode = "/mjpg-lq",
  cat_recognize_mode = "/mjpg-hq/cat-recognize",
  cat_recognize_extended_mode = "/mjpg-hq/cat-recognize-extended",
  human_recognize_mode = "/mjpg-hq/human-face-recognize",
  human_body_recognize_mode = "/mjpg-hq/human-body-recognize",
  enhanced_high_quality_mode = "/mjpg-xhq",
  extra_low_quality_mode = "/mjpg-xlq",
  low_quality_png_mode = "/mpng-lq",
}
