import type { ControllerActionName } from "@/features/controller/store";
import { objectKeysToOptions } from "@/features/settings/util";

export const defaultKeybindinds: Partial<
  Record<ControllerActionName, string[]>
> = {
  accelerate: ["w"],
  decelerate: ["s"],
  left: ["a"],
  right: ["d"],
  stop: ["Space"],
  decreaseCamPan: ["ArrowLeft"],
  decreaseCamTilt: ["ArrowDown"],
  increaseCamPan: ["ArrowRight"],
  increaseCamTilt: ["ArrowUp"],
  decreaseMaxSpeed: ["-"],
  increaseMaxSpeed: ["="],
  getDistance: ["u"],
  playMusic: ["m"],
  playSound: ["o"],
  resetCameraRotate: ["0"],
  sayText: ["k"],
  takePhoto: ["t"],
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
  playSound: "Play Sound",
  sayText: "Say Text",
  takePhoto: "Make photo",
};

export const allCommandOptions = objectKeysToOptions(
  defaultKeybindinds,
  commandLabels,
);
