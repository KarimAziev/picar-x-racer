import { generateMultiplesOf32 } from "@/util/number";
import { numberSequence } from "@/util/cycleValue";
import { SettingsTab } from "@/features/settings/enums";
import { OverlayStyle } from "@/features/detection";
import { startCase } from "@/util/str";
import { Settings } from "@/features/settings/interface";
import { FlattenBooleanObjectKeys } from "@/util/ts-helpers";

export const generalSwitchSettings: {
  [P in FlattenBooleanObjectKeys<Settings["general"]>]: {
    label: string;
    description: string;
  };
} = {
  text_info_view: {
    label: "Gauges View",
    description:
      "Toggle the display of text information (e.g., camera tilt, camera pan, servo direction, etc.) on or off.",
  },
  speedometer_view: {
    label: "Speedometer",
    description: "Toggle the speedometer display on or off.",
  },
  robot_3d_view: {
    label: "3D View of the Car",
    description: "Toggle the 3D view of the car on or off.",
  },
  text_to_speech_input: {
    label: "Text-to-Speech Input",
    description:
      "Toggle the display of text-to-speech input on the main screen.",
  },
  show_player: {
    label: "Music Player",
    description: "Toggle the display of the music player.",
  },
  show_object_detection_settings: {
    label: "Object Detection Panel",
    description:
      "Toggle the display of the object detection panel on the main screen.",
  },
  auto_download_photo: {
    label: "Auto-Download Photos",
    description: "Toggle the automatic download of captured photos.",
  },
  auto_download_video: {
    label: "Auto-Download Videos",
    description: "Toggle the automatic download of recorded videos.",
  },
  virtual_mode: {
    label: "Virtual 3D Mode",
    description: "Toggle replacing the camera view with a 3D model.",
  },
  show_battery_indicator: {
    label: "Battery Level",
    description: "Toggle the display of the battery level indicator.",
  },
  show_connections_indicator: {
    label: "Connections Counter",
    description: "Toggle the display of the active connections counter.",
  },
  show_auto_measure_distance_button: {
    label: "Measure Distance Button",
    description: "Toggle the display of the auto-measure distance button.",
  },
  show_audio_stream_button: {
    label: "Audio Stream Button",
    description: "Toggle the display of the audio stream icon button.",
  },
  show_photo_capture_button: {
    label: "Photo Capture Button",
    description: "Toggle the display of the photo capture icon button.",
  },
  show_video_record_button: {
    label: "Video Record Button",
    description: "Toggle the display of the video record icon button.",
  },
  show_shutdown_reboot_button: {
    label: "Power Off Button",
    description:
      "Toggles the display of the shutdown and reboot control buttons.",
  },
  show_fullscreen_button: {
    label: "Full Screen Button",
    description: "Toggle the display of the fullscreen icon button.",
  },
  show_avoid_obstacles_button: {
    label: "Avoid Obstacles Button",
    description:
      "Whether to display the button to toggle the avoid obstacle mode.",
  },
  show_dark_theme_toggle: {
    label: "Dark Theme Toggle",
    description:
      "Whether to display the dark theme toggle button in the top right corner of the screen.",
  },
} as const;

export const saveableTabs = {
  [SettingsTab.GENERAL]: true,
  [SettingsTab.KEYBINDINGS]: false,
  [SettingsTab.CALIBRATION]: false,
  [SettingsTab.TTS]: true,
  [SettingsTab.PHOTOS]: false,
  [SettingsTab.MODELS]: true,
};

export const imgSizeOptions = generateMultiplesOf32(2000).map((value) => ({
  value,
  label: `${value}`,
}));
export const overlayStyleOptions = Object.values(OverlayStyle).map((value) => ({
  value,
  label: startCase(value),
}));

export const videoQualityOptions = numberSequence(10, 100, 10).map((value) => ({
  value: value,
  label: `${value}`,
}));
