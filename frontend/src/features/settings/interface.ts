import { ControllerActionName } from "@/features/controller/store";
import type { DetectionSettings } from "@/features/detection";
import type { StreamSettings } from "@/features/settings/stores/stream";
import type { CameraSettings } from "@/features/settings/stores/camera";
import { MusicMode } from "@/features/music";
import { FlattenBooleanObjectKeys, FlattenObject } from "@/util/ts-helpers";

export type APIMediaType = "image" | "sound" | "music" | "data";

export interface ValueLabelOption {
  value: string;
  label: string;
}

export interface Settings {
  general: General;
  robot: Robot;
  tts: TTS;
  battery: Battery;
  music: Music;
  camera: CameraSettings;
  stream: StreamSettings;
  detection: DetectionSettings;
  keybindings: Partial<Record<ControllerActionName, string[] | null>>;
}

export type ToggleableKey = FlattenBooleanObjectKeys<
  Required<Pick<Settings, "general" | "robot">>
>;
export type AllProps = FlattenObject<Settings>;

export interface Battery {
  full_voltage: number;
  warn_voltage: number;
  danger_voltage: number;
  min_voltage: number;
  auto_measure_seconds: number;
  cache_seconds: number;
}

export interface General {
  robot_3d_view: boolean;
  speedometer_view: boolean;
  text_info_view: boolean;
  auto_download_photo: boolean;
  auto_download_video: boolean;
  virtual_mode: boolean;
  show_player: boolean;
  show_object_detection_settings: boolean;
  text_to_speech_input: boolean;
  show_battery_indicator: boolean;
  show_connections_indicator: boolean;
  show_auto_measure_distance_button: boolean;
  show_audio_stream_button: boolean;
  show_photo_capture_button: boolean;
  show_video_record_button: boolean;
  show_shutdown_reboot_button: boolean;
  show_fullscreen_button: boolean;
  show_avoid_obstacles_button: boolean;
}

export interface Music {
  mode: MusicMode;
  order: string[];
}

export interface Robot {
  max_speed: number;
  auto_measure_distance_mode: boolean;
  auto_measure_distance_delay_ms: number;
}

export interface TTS {
  default_tts_language: string;
  texts: Text[];
}

export interface Text {
  text: string;
  language: string;
  default?: boolean;
}

export interface RemoveFileResponse {
  success: boolean;
  filename: string;
  error: string | null;
}
