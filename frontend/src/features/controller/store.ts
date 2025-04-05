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
  useSettingsStore,
  usePopupStore,
  useBatteryStore,
  useDistanceStore,
  useCameraStore,
  useStreamStore,
  useRobotStore,
} from "@/features/settings/stores";
import { useDetectionStore } from "@/features/detection";
import { useMessagerStore } from "@/features/messager";
import { useMusicStore } from "@/features/music";
import { useImageStore } from "@/features/files/stores";
import { wait } from "@/util/wait";
import { roundToNearestTen } from "@/util/number";
import { takePhotoEffect } from "@/util/dom";
import { useAppSyncStore } from "@/features/syncer";
import type { Data as RobotData } from "@/features/settings/stores/robot";

export const ACCELERATION = 10;
export const MIN_SPEED = ACCELERATION;

export interface Modes {
  /**
   * Whether avoid obstacles mode is enabled.
   */
  avoidObstacles: boolean;
  /**
   * Whether calibration mode is enabled.
   */
  calibrationMode: boolean;
  ledBlinking: boolean;
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
  ledBlinking: false,
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
      const settingsStore = useSettingsStore();
      const batteryStore = useBatteryStore();
      const robotStore = useRobotStore();
      const handleMessage = (data: WSMessageData) => {
        if (!data) {
          return;
        }
        const { type, payload, error } = data;

        switch (type) {
          case "battery": {
            batteryStore.$patch({
              voltage: payload.voltage,
              percentage: payload.percentage,
              error: undefined,
              loading: false,
            });
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

          case "distance":
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
            robotStore.data = payload;
            break;

          case "saveCalibration":
            robotStore.data = payload;
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
                } else if (k === "autoMeasureDistanceMode") {
                  settingsStore.data.robot.auto_measure_distance_mode = value;
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
      const syncStore = useAppSyncStore();
      if (syncStore.active_connections <= 1 && this.speed !== 0) {
        this.stop();
      }

      this.model?.cleanup();
      this.model = null;
    },

    sendMessage(message: any): void {
      this.model?.send(message);
    },

    resetAll() {
      const settingsStore = useSettingsStore();

      const actionValueLists = [
        [
          settingsStore.data.robot.auto_measure_distance_mode,
          false,
          this.toggleAutoMeasureDistanceMode,
        ],
        [this.avoidObstacles, false, this.toggleAvoidObstaclesMode],
        [this.speed, 0, this.stop],
        [this.servoAngle, 0, this.resetDirServoAngle],
        [this.camPan, 0, this.resetCamPan],
        [this.camTilt, 0, this.resetCamTilt],
      ] as const;

      actionValueLists.forEach(([value, requiredValue, action]) => {
        if (value !== requiredValue) {
          action();
        }
      });
    },

    // command workers
    setMaxSpeed(value: number) {
      const robotStore = useRobotStore();
      const newValue = constrain(MIN_SPEED, robotStore.maxSpeed, value);
      if (newValue !== this.maxSpeed) {
        this.sendMessage({ action: "setMaxSpeed", payload: newValue });
      }
    },
    setCamTiltAngle(angle: number): void {
      const robotStore = useRobotStore();
      const nextAngle = Math.trunc(
        constrain(
          robotStore.data.cam_tilt_servo.min_angle,
          robotStore.data.cam_tilt_servo.max_angle,
          angle,
        ),
      );
      this.sendMessage({ action: "setCamTiltAngle", payload: nextAngle });
    },

    setCamPanAngle(servoAngle: number): void {
      const robotStore = useRobotStore();
      const nextAngle = Math.trunc(
        constrain(
          robotStore.data.cam_pan_servo.min_angle,
          robotStore.data.cam_pan_servo.max_angle,
          servoAngle,
        ),
      );
      this.sendMessage({ action: "setCamPanAngle", payload: nextAngle });
    },

    move(speed: number, direction: number) {
      const robotStore = useRobotStore();
      speed = constrain(0, this.maxSpeed, robotStore.maxSpeed);
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
      const robotStore = useRobotStore();
      const nextAngle = constrain(
        robotStore.data.steering_servo.min_angle,
        robotStore.data.steering_servo.max_angle,
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
          settingsStore.data.tts.texts.find((item) => item.default) ||
          settingsStore.data.tts.texts[0];
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

      if (file && settingsStore.data.general.auto_download_photo) {
        await imageStore.downloadFile(file);
      }
    },
    toggleAvoidObstaclesMode() {
      this.sendMessage({ action: "avoidObstacles" });
    },
    left() {
      const robotStore = useRobotStore();
      this.setDirServoAngle(robotStore.data.steering_servo.min_angle);
    },
    right() {
      const robotStore = useRobotStore();
      this.setDirServoAngle(robotStore.data.steering_servo.max_angle);
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
    reverseLeftMotor() {
      this.sendMessage({ action: "reverseLeftMotor" });
    },
    reverseRightMotor() {
      this.sendMessage({ action: "reverseRightMotor" });
    },
    saveCalibration() {
      this.sendMessage({ action: "saveCalibration" });
    },
    saveRobotConfig(payload: RobotData) {
      this.sendMessage({ action: "saveConfig", payload });
    },
    servoTest() {
      this.sendMessage({ action: "servoTest" });
    },
    resetCalibration() {
      this.sendMessage({ action: "resetCalibration" });
    },
    updateServoDirCali(value: number) {
      this.sendMessage({ action: "updateServoDirCali", payload: value });
    },
    updateCamPanCali(value: number) {
      this.sendMessage({ action: "updateCamPanCali", payload: value });
    },
    updateCamTiltCali(value: number) {
      this.sendMessage({ action: "updateCamTiltCali", payload: value });
    },
    updateLeftMotorCaliDir(value: number) {
      this.sendMessage({ action: "updateLeftMotorCaliDir", payload: value });
    },
    updateRightMotorCaliDir(value: number) {
      this.sendMessage({ action: "updateRightMotorCaliDir", payload: value });
    },
    resetMCU() {
      const messager = useMessagerStore();
      messager.info("Resetting MCU");
      this.sendMessage({ action: "resetMCU" });
    },
    toggleLEDblinking() {
      const action = this.ledBlinking ? "stopLED" : "startLED";
      this.sendMessage({
        action: action,
      });
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
      settingsStore.toggleSettingsProp("general.text_info_view");
    },
    toggleSpeedometerView() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("general.speedometer_view");
    },
    toggleCarModelView() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("general.robot_3d_view");
    },
    toggleAutoDownloadPhoto() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("general.auto_download_photo");
    },
    toggleAutoMeasureDistanceMode() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("robot.auto_measure_distance_mode");
      this.sendMessage({
        action: settingsStore.data.robot.auto_measure_distance_mode
          ? "startAutoMeasureDistance"
          : "stopAutoMeasureDistance",
      });
    },
    toggleVirtualMode() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("general.virtual_mode");
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
      const streamStore = useStreamStore();
      await streamStore.toggleRecording();
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
