import { useControllerStore } from "@/features/controller/store";

export type APIMediaType = "image" | "sound" | "music";

export type ControllerStore = ReturnType<typeof useControllerStore>;

// export type ControllerKeybindings = P i
export type Keybindings = Partial<{
  forward: string[];
  backward: string[];
  left: string[];
  right: string[];
  takePhoto: string[];
  playMusic: string[];
  playSound: string[];
  resetCameraRotate: string[];
  sayText: string[];
  increaseMaxSpeed: string[];
  decreaseMaxSpeed: string[];
  increaseCamPan: string[];
  decreaseCamPan: string[];
  increaseCamTilt: string[];
  decreaseCamTilt: string[];
  getDistance: string[];
}>;
