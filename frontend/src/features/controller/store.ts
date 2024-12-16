import type { ShallowRef } from "vue";
import { defineStore } from "pinia";
import { SettingsTab } from "@/features/settings/enums";
import { isNumber, isPlainObject, isString } from "@/util/guards";
import { constrain } from "@/util/constrain";
import type {
  MethodsWithoutParams,
  ExcludePropertiesWithPrefix,
} from "@/util/ts-helpers";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";
import {
  useImageStore,
  useSettingsStore,
  usePopupStore,
  useBatteryStore,
  useCalibrationStore,
  useDistanceStore,
  useCameraStore,
  useStreamStore,
} from "@/features/settings/stores";
import { useDetectionStore } from "@/features/detection";
import { useMessagerStore } from "@/features/messager";
import { useMusicStore } from "@/features/music";
import { wait } from "@/util/wait";
import { roundToNearestTen } from "@/util/number";
import { takePhotoEffect } from "@/util/dom";

export const ACCELERATION = 10;
export const CAM_PAN_MIN = -90;
export const CAM_PAN_MAX = 90;
export const CAM_TILT_MIN = -35;
export const CAM_TILT_MAX = 65;
export const SERVO_DIR_ANGLE_MIN = -30;
export const SERVO_DIR_ANGLE_MAX = 30;
export const MIN_SPEED = 10;
export const MAX_SPEED = 100;

export interface Modes {
  /**
   * Whether avoid obstacles mode is enabled.
   */
  avoidObstacles: boolean;
  /**
   * Whether calibration mode is enabled.
   */
  calibrationMode: boolean;
}

export interface Gauges {
  /** Current speed of the car, from 0 to 100 */
  speed: number;
  /**
   * Current direction: -1 for backward, 1 for forward, 0 for stopped
   */
  direction: number;
  /**
   * Current direction servo
   */
  servoAngle: number;
  /**
   * Current maximum speed for accelerating or decelerating
   */
  maxSpeed: number;
  /**
   * Camera pan angle
   */
  camPan: number;
  /**
   * Camera tilt angle
   */
  camTilt: number;
}

export interface StoreState extends Gauges, Modes {
  model: ShallowRef<WebSocketModel> | null;
}

const defaultGauges: Gauges = {
  speed: 0,
  direction: 0,
  servoAngle: 0,
  maxSpeed: 80,
  camPan: 0,
  camTilt: 0,
} as const;

const modes: Modes = {
  avoidObstacles: false,
  calibrationMode: false,
};

const defaultState: StoreState = {
  ...defaultGauges,
  ...modes,
  model: null,
} as const;

export interface WSMessageData {
  type: string;
  payload: any;
  error?: string;
}

export const useControllerStore = defineStore("controller", {
  state: (): StoreState => ({ ...defaultState }),
  actions: {
    initializeWebSocket() {
      if (this.model?.connected || this.model?.loading) {
        return;
      }
      const messager = useMessagerStore();
      const distanceStore = useDistanceStore();
      const calibrationStore = useCalibrationStore();
      const batteryStore = useBatteryStore();
      const handleMessage = (data: WSMessageData) => {
        if (!data) {
          return;
        }
        const { type, payload, error } = data;

        switch (type) {
          case "battery": {
            batteryStore.voltage = payload;
            break;
          }

          case "info": {
            messager.info(payload, {
              immediately: true,
            });
            break;
          }

          case "error": {
            messager.error(payload, {
              immediately: true,
            });
            break;
          }

          case "getDistance":
            if (error) {
              messager.error(error, "distance error");
            } else {
              distanceStore.distance = payload;
            }

            break;
          case "stop":
            this.direction = 0;
            this.speed = 0;
            break;

          case "setServoDirAngle":
            this.servoAngle = payload;
            break;

          case "setCamPanAngle":
            this.camPan = payload;
            break;

          case "setCamTiltAngle":
            this.camTilt = payload;
            break;

          case "avoidObstacles":
            this.avoidObstacles = payload;
            messager.info(`Avoid Obstacles: ${payload}`, {
              immediately: true,
            });
            break;

          case "updateCalibration":
            calibrationStore.data = payload;
            break;

          case "saveCalibration":
            calibrationStore.data = payload;
            this.calibrationMode = false;
            messager.info(`Calibration saved`);
            break;

          default:
            if (data.error) {
              messager.error(data.error);
            } else if (isPlainObject(payload)) {
              Object.entries(payload).forEach(([k, value]) => {
                if (k in defaultGauges && isNumber(value)) {
                  this[k as keyof Gauges] = value as Gauges[keyof Gauges];
                } else if (k in modes && (value === false || value === true)) {
                  const mode = k as keyof typeof modes;
                  const currMode = this[mode];
                  if (currMode !== value) {
                    this[mode] = value as boolean;
                    messager.info(`${k}: ${value}`, {
                      immediately: true,
                    });
                  }
                }
              });
            } else if (
              isNumber(payload) &&
              isString(type) &&
              type in defaultGauges
            ) {
              this[type as keyof Gauges] = payload;
            }
        }
      };

      this.model = useWebSocket({
        url: "px/ws",
        port: 8001,
        onMessage: handleMessage,
        logPrefix: "px",
      });
      this.model.initWS();
    },

    cleanup() {
      if (this.speed !== 0) {
        this.stop();
      }

      if (this.servoAngle !== 0) {
        this.resetDirServoAngle();
      }

      if (this.camPan !== 0) {
        this.resetCamPan();
      }
      if (this.camTilt !== 0) {
        this.resetCamTilt();
      }

      this.model?.cleanup();
      this.model = null;
    },

    sendMessage(message: any): void {
      this.model?.send(message);
    },
    // command workers
    setMaxSpeed(value: number) {
      const newValue = constrain(MIN_SPEED, MAX_SPEED, value);
      if (newValue !== this.maxSpeed) {
        this.sendMessage({ action: "setMaxSpeed", payload: newValue });
      }
    },
    setCamTiltAngle(angle: number): void {
      const nextAngle = Math.trunc(
        constrain(CAM_TILT_MIN, CAM_TILT_MAX, angle),
      );
      this.sendMessage({ action: "setCamTiltAngle", payload: nextAngle });
    },

    setCamPanAngle(servoAngle: number): void {
      const nextAngle = Math.trunc(
        constrain(CAM_PAN_MIN, CAM_PAN_MAX, servoAngle),
      );
      this.sendMessage({ action: "setCamPanAngle", payload: nextAngle });
    },

    move(speed: number, direction: number) {
      speed = constrain(0, this.maxSpeed, speed);
      if (this.speed !== speed || this.direction !== direction) {
        this.sendMessage({
          action: "move",
          payload: {
            direction,
            speed,
          },
        });
      }
    },

    forward(speed: number) {
      this.move(speed, 1);
    },

    backward(speed: number) {
      this.move(speed, -1);
    },

    setDirServoAngle(servoAngle: number) {
      const nextAngle = constrain(
        SERVO_DIR_ANGLE_MIN,
        SERVO_DIR_ANGLE_MAX,
        servoAngle,
      );
      this.sendMessage({ action: "setServoDirAngle", payload: nextAngle });
    },
    // commands
    accelerate() {
      this.forward(Math.min(this.speed + ACCELERATION, this.maxSpeed));
    },

    decelerate() {
      const nextSpeed = Math.min(this.speed + ACCELERATION, this.maxSpeed);
      this.backward(nextSpeed);
    },

    async slowdown() {
      const nextSpeed = roundToNearestTen(
        this.speed > 10
          ? Math.max(this.speed / 2, 0)
          : this.speed === 10
            ? Math.max(this.speed - 10, 0)
            : this.speed,
      );
      if (nextSpeed === 0) {
        this.stop();
      } else if (this.direction === 1) {
        this.forward(nextSpeed);
        await wait(100);
        if (nextSpeed === this.speed) {
          this.stop();
        }
      } else if (this.direction === -1) {
        this.backward(nextSpeed);
        await wait(100);
        if (nextSpeed === this.speed) {
          this.stop();
        }
      }
    },
    stop() {
      this.sendMessage({ action: "stop" });
    },
    increaseMaxSpeed() {
      this.setMaxSpeed(this.maxSpeed + ACCELERATION);
    },

    decreaseMaxSpeed() {
      this.setMaxSpeed(this.maxSpeed - ACCELERATION);
    },

    resetCamTilt() {
      this.setCamTiltAngle(0);
    },

    increaseCamTilt() {
      this.setCamTiltAngle(this.camTilt + 5);
    },

    decreaseCamTilt() {
      this.setCamTiltAngle(this.camTilt - 5);
    },

    increaseCamPan() {
      this.setCamPanAngle(this.camPan + 5);
    },

    resetCamPan() {
      this.setCamPanAngle(0);
    },

    decreaseCamPan() {
      this.setCamPanAngle(this.camPan - 5);
    },

    resetCameraRotate() {
      this.resetCamPan();
      this.resetCamTilt();
    },

    resetDirServoAngle(): void {
      this.setDirServoAngle(0);
    },

    async sayText() {
      const settingsStore = useSettingsStore();
      if (!settingsStore.text) {
        const item =
          settingsStore.data.texts.find((item) => item.default) ||
          settingsStore.data.texts[0];
        settingsStore.text = item.text;
        settingsStore.language = item.language;
      }

      if (settingsStore.text && settingsStore.language) {
        await settingsStore.speakText(
          settingsStore.text,
          settingsStore.language,
        );
      }
    },

    nextText() {
      const settingsStore = useSettingsStore();
      settingsStore.prevText();
    },
    prevText() {
      const settingsStore = useSettingsStore();
      settingsStore.nextText();
    },

    async getDistance() {
      const distanceStore = useDistanceStore();

      await distanceStore.fetchDistance();
    },

    async takePhoto() {
      const imageStore = useImageStore();
      const cameraStore = useCameraStore();
      const settingsStore = useSettingsStore();
      const file = await cameraStore.capturePhoto();

      if (file) {
        takePhotoEffect();
      }

      if (file && settingsStore.data.auto_download_photo) {
        await imageStore.downloadFile(file);
      }
    },
    toggleAvoidObstaclesMode() {
      this.sendMessage({ action: "avoidObstacles" });
    },
    left() {
      this.setDirServoAngle(SERVO_DIR_ANGLE_MIN);
    },
    right() {
      this.setDirServoAngle(SERVO_DIR_ANGLE_MAX);
    },

    toggleCalibration() {
      const popupStore = usePopupStore();
      const messager = useMessagerStore();
      this.calibrationMode = !this.calibrationMode;
      if (this.calibrationMode) {
        this.stop();
        this.resetCameraRotate();
        this.resetDirServoAngle();
        this.maxSpeed = MIN_SPEED;
        popupStore.isOpen = false;
        messager.info("Starting calibration");
      } else {
        messager.info("Calibration finished");
      }
    },
    increaseCamPanCali() {
      this.sendMessage({ action: "increaseCamPanCali" });
    },
    decreaseCamPanCali() {
      this.sendMessage({ action: "decreaseCamPanCali" });
    },
    increaseCamTiltCali() {
      this.sendMessage({ action: "increaseCamTiltCali" });
    },
    decreaseCamTiltCali() {
      this.sendMessage({ action: "decreaseCamTiltCali" });
    },
    increaseServoDirCali() {
      this.sendMessage({ action: "increaseServoDirCali" });
    },
    decreaseServoDirCali() {
      this.sendMessage({ action: "decreaseServoDirCali" });
    },
    saveCalibration() {
      this.sendMessage({ action: "saveCalibration" });
    },
    servoTest() {
      this.sendMessage({ action: "servoTest" });
    },
    resetCalibration() {
      this.sendMessage({ action: "resetCalibration" });
    },
    // UI commands
    getBatteryVoltage() {
      const batteryStore = useBatteryStore();
      batteryStore.fetchBatteryStatus();
    },
    openShortcutsSettings() {
      const popupStore = usePopupStore();
      popupStore.tab = SettingsTab.KEYBINDINGS;
      popupStore.isOpen = true;
    },
    openGeneralSettings() {
      const popupStore = usePopupStore();
      popupStore.tab = SettingsTab.GENERAL;
      popupStore.isOpen = true;
    },
    toggleTextInfo() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("text_info_view");
    },
    toggleSpeedometerView() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("speedometer_view");
    },
    toggleCarModelView() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("car_model_view");
    },
    toggleAutoDownloadPhoto() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("auto_download_photo");
    },
    toggleAutoMeasureDistanceMode() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("auto_measure_distance_mode");
    },
    toggleVirtualMode() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("virtual_mode");
    },
    async increaseFPS() {
      const camStore = useCameraStore();
      await camStore.increaseFPS();
    },
    async decreaseFPS() {
      const camStore = useCameraStore();
      await camStore.decreaseFPS();
    },
    async increaseDimension() {
      const camStore = useCameraStore();
      await camStore.increaseDimension();
    },
    async decreaseDimension() {
      const camStore = useCameraStore();
      await camStore.decreaseDimension();
    },
    async increaseQuality() {
      const streamStore = useStreamStore();
      await streamStore.increaseQuality();
    },
    async decreaseQuality() {
      const streamStore = useStreamStore();
      await streamStore.decreaseQuality();
    },
    async toggleDetection() {
      const detectionStore = useDetectionStore();
      await detectionStore.toggleDetection();
    },
    async nextEnhanceMode() {
      const streamStore = useStreamStore();
      await streamStore.nextEnhanceMode();
    },

    async prevEnhanceMode() {
      const streamStore = useStreamStore();
      await streamStore.prevEnhanceMode();
    },
    async toggleVideoRecord() {
      const settingsStore = useSettingsStore();
      const streamStore = useStreamStore();
      await streamStore.toggleRecording(settingsStore.data.auto_download_video);
    },
    async increaseVolume() {
      const musicStore = useMusicStore();
      await musicStore.increaseVolume();
    },
    async decreaseVolume() {
      const musicStore = useMusicStore();
      await musicStore.decreaseVolume();
    },
    async playMusic() {
      const musicStore = useMusicStore();
      await musicStore.togglePlaying();
    },

    async playNextMusicTrack() {
      const musicStore = useMusicStore();
      await musicStore.nextTrack();
    },

    async playPrevMusicTrack() {
      const musicStore = useMusicStore();
      await musicStore.prevTrack();
    },
    toggleAudioStreaming() {
      const musicStore = useMusicStore();
      musicStore.toggleStreaming();
    },
  },
});

export type ControllerState = Omit<
  ReturnType<typeof useControllerStore>,
  keyof ReturnType<typeof defineStore>
>;

export type ControllerActions = Omit<
  ExcludePropertiesWithPrefix<"$", MethodsWithoutParams<ControllerState>>,
  "initializeWebSocket" | "cleanup"
>;

export type ControllerActionName = keyof ControllerActions;
