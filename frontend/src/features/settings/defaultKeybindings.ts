import type { ControllerActionName } from "@/features/controller/store";
import { objectKeysToOptions } from "@/features/settings/util";

export const defaultKeybindinds: Partial<
  Record<ControllerActionName, string[]>
> = {
  accelerate: ["w"],
  decelerate: ["s"],
  decreaseCamPan: ["ArrowLeft"],
  decreaseCamTilt: ["ArrowDown"],
  decreaseMaxSpeed: ["-"],
  decreaseQuality: ["<"],
  getBatteryVoltage: ["b"],
  getDistance: ["u"],
  increaseCamPan: ["ArrowRight"],
  increaseCamTilt: ["ArrowUp"],
  increaseMaxSpeed: ["="],
  increaseQuality: [">"],
  left: ["a"],
  openGeneralSettings: ["h"],
  openShortcutsSettings: ["?"],
  playMusic: ["m"],
  resetCameraRotate: ["0"],
  right: ["d"],
  sayText: ["k"],
  slowdown: ["Space"],
  takePhoto: ["t"],
  toggleAvoidObstaclesMode: ["O"],
  toggleCarModelView: ["M"],
  toggleSpeedometerView: ["N"],
  toggleTextInfo: ["I"],
  toggleAudioStreaming: ["."],
  toggleVirtualMode: ["*"],
  toggleAutoMeasureDistanceMode: ["U"],
  toggleAutoDownloadPhoto: ["P"],
  toggleCalibration: ["C"],
  increaseFPS: ["F"],
  decreaseFPS: ["S"],
  increaseDimension: ["]"],
  decreaseDimension: ["["],
  nextEnhanceMode: ["e"],
  prevEnhanceMode: ["E"],
  toggleDetection: ["r"],
  increaseVolume: ["PageUp"],
  decreaseVolume: ["PageDown"],
  playNextMusicTrack: ["2"],
  playPrevMusicTrack: ["1"],
  nextText: ["4"],
  prevText: ["3"],
  toggleVideoRecord: ["v"],
};

export const commandLabels: Record<string, string> = {
  accelerate: "Move Forward",
  decelerate: "Move Backward",
  left: "Move left",
  right: "Move right",
  stop: "Stop",
  decreaseCamPan: "Camera Left",
  decreaseCamTilt: "Camera Down",
  increaseCamPan: "Camera Right",
  increaseCamTilt: "Camera Up",
  resetCameraRotate: "Reset Camera Orientation",
  decreaseMaxSpeed: "Decrease max speed",
  increaseMaxSpeed: "Increase max speed",
  getDistance: "Measure distance",
  playMusic: "Play music",
  sayText: "Say Text",
  takePhoto: "Make photo",
  getBatteryVoltage: "Show Battery Voltage",
  openShortcutsSettings: "Open Shortcuts Settings",
  openGeneralSettings: "Open General Settings",
  increaseQuality: "Increase Video Quality",
  decreaseQuality: "Decrease Video Quality",
  toggleAvoidObstaclesMode: "Toggle Avoid Obstacles Mode",
  toggleCalibration: "Toggle Calibration Mode",
  increaseFPS: "Increase FPS",
  decreaseFPS: "Decrease FPS",
  increaseDimension: "Increase dimension",
  decreaseDimension: "Decrease dimension",
  playNextMusicTrack: "Next music track",
  playPrevMusicTrack: "Previous music track",
  nextText: "Next text to speech",
  prevText: "Previous text to speech",
  toggleVideoRecord: "Toggle Video Recording",
};

export const calibrationModeRemap: Partial<
  Record<ControllerActionName, ControllerActionName>
> = {
  left: "decreaseServoDirCali",
  right: "increaseServoDirCali",
  decreaseCamTilt: "decreaseCamTiltCali",
  increaseCamTilt: "increaseCamTiltCali",
  decreaseCamPan: "decreaseCamPanCali",
  increaseCamPan: "increaseCamPanCali",
  resetCameraRotate: "resetCalibration",
};

export const allCommandOptions = objectKeysToOptions(
  defaultKeybindinds,
  commandLabels,
);
