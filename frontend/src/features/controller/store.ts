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
import { useAuxiliarySensorStore } from "@/features/sensors";
import type { ServoConfig } from "@/features/settings/stores/robot";

const isCalibrationStepReversed = (config: ServoConfig) => {
  // Offsets add to the hardware angle; movement also applies direction and mode.
  return config.reverse !== (config.calibration_mode === "negative");
};

// Commands and telemetry use logical angles; the backend applies servo reversal.
const constrainServoCommand = (config: ServoConfig, angle: number) =>
  constrain(
    config.reverse ? -config.max_angle : config.min_angle,
    config.reverse ? -config.min_angle : config.max_angle,
    angle,
  );

export const ACCELERATION = 10;
export const MIN_SPEED = ACCELERATION;

export interface UpdatePayloadResponse {
  speed: number;
  direction: number;
  servoAngle: number;
  camPan: number;
  camTilt: number;
  maxSpeed: number;
  distance: number;
  avoidObstacles: boolean;
  autoMeasureDistanceMode: boolean;
  ledBlinking: boolean;
  motionControlEnabled: boolean;
  servoTuningActive?: boolean;
  robotMode: RobotMode;
  motionGeneration: number;
  motionReason: string | null;
  motionSource: string | null;
  emergencyStop: boolean;
  motionFault: string | null;
}

export type RobotMode =
  | "legacy"
  | "disarmed"
  | "manual"
  | "autonomous"
  | "calibration"
  | "estop"
  | "fault";

export interface Modes {
  /**
   * Whether avoid obstacles mode is enabled.
   */
  avoidObstacles: boolean;
  /**
   * Whether calibration mode is enabled.
   */
  calibrationMode: boolean;
  /**
   * Whether led is blinking
   */
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

export type UpdateCombinedPayload = Partial<{
  [K in keyof Gauges]: Gauges[K] | null;
}>;

export interface StoreState extends Gauges, Modes {
  model: ShallowRef<WebSocketModel> | null;
  motionHeartbeat: ReturnType<typeof setInterval> | null;
  requestedSpeed: number;
  requestedDirection: number;
  requestedServoAngle: number | null;
  motionControlEnabled: boolean;
  robotMode: RobotMode;
  motionGeneration: number;
  motionReason: string | null;
  motionSource: string | null;
  emergencyStopActive: boolean;
  motionFault: string | null;
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
  motionHeartbeat: null,
  requestedSpeed: 0,
  requestedDirection: 0,
  requestedServoAngle: null,
  motionControlEnabled: false,
  robotMode: "legacy",
  motionGeneration: 0,
  motionReason: null,
  motionSource: null,
  emergencyStopActive: false,
  motionFault: null,
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
      const auxiliarySensorStore = useAuxiliarySensorStore();
      const handleMessage = (data: WSMessageData) => {
        if (!data) {
          return;
        }
        const { type, payload, error } = data;

        switch (type) {
          case "update": {
            const typedPayload: UpdatePayloadResponse = payload;
            const tuningActive = typedPayload.servoTuningActive ?? false;
            if (tuningActive !== this.calibrationMode)
              this.requestedServoAngle = null;
            this.calibrationMode = tuningActive;
            this.speed = typedPayload.speed;
            this.direction = typedPayload.direction;
            this.servoAngle = typedPayload.servoAngle;
            if (
              this.requestedServoAngle !== null &&
              Math.abs(this.servoAngle - this.requestedServoAngle) < 0.001
            ) {
              this.requestedServoAngle = null;
            }
            this.camTilt = typedPayload.camTilt;
            this.camPan = typedPayload.camPan;
            this.maxSpeed = typedPayload.maxSpeed;
            this.avoidObstacles = typedPayload.avoidObstacles;
            this.ledBlinking = typedPayload.ledBlinking;
            this.motionControlEnabled = typedPayload.motionControlEnabled;
            this.robotMode = typedPayload.robotMode;
            this.motionGeneration = typedPayload.motionGeneration;
            this.motionReason = typedPayload.motionReason;
            this.motionSource = typedPayload.motionSource ?? null;
            this.emergencyStopActive = typedPayload.emergencyStop;
            this.motionFault = typedPayload.motionFault;
            const robotSettings = settingsStore.data?.robot;
            if (robotSettings) {
              robotSettings.auto_measure_distance_mode =
                typedPayload.autoMeasureDistanceMode;
            }

            break;
          }
          case "battery": {
            batteryStore.mergeBatteryMetrics(payload);
            break;
          }

          case "auxiliary_sensors": {
            auxiliarySensorStore.setReadings(payload);
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
              messager.error(error, "Ultrasonic measurement error");
            } else {
              distanceStore.distance = payload.distance;
              distanceStore.speed = payload.speed;
            }

            break;
          case "stop":
            this.direction = 0;
            this.speed = 0;
            break;

          case "setServoDirAngle": {
            this.servoAngle = payload;
            break;
          }

          case "setCamPanAngle": {
            this.camPan = payload;
            break;
          }

          case "setCamTiltAngle":
            this.camTilt = payload;
            break;

          case "avoidObstacles":
            this.avoidObstacles = payload;
            messager.info(`Ultrasonic obstacle avoidance: ${payload}`, {
              immediately: true,
            });
            break;

          case "robot_partial_settings":
            robotStore.partialData = payload;
            Object.entries(payload).forEach(([key, value]) => {
              robotStore.data[key as keyof typeof robotStore.data] =
                value as any;
            });

            break;
          case "robot_settings":
            robotStore.data = payload;
            break;

          case "updateCalibration":
            this.requestedServoAngle = null;
            robotStore.mergeCalibrationData(payload);
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
                  const robotSettings = settingsStore.data?.robot;
                  if (robotSettings && typeof value === "boolean") {
                    robotSettings.auto_measure_distance_mode = value;
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
        port: +(import.meta.env.VITE_WS_APP_PORT || "8001"),
        onMessage: handleMessage,
        logPrefix: "px",
        onOpen: async () => {
          await robotStore.fetchData();
        },
        onClose: () => {
          this.clearMotionHeartbeat();
          this.requestedSpeed = 0;
          this.requestedDirection = 0;
          this.requestedServoAngle = null;
        },
        queueMessages: false,
      });
      this.model.initWS();
    },

    cleanup() {
      const syncStore = useAppSyncStore();
      if (syncStore.active_connections <= 1 && this.speed !== 0) {
        this.stop();
      }

      this.clearMotionHeartbeat();

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
      ] as const;

      actionValueLists.forEach(([value, requiredValue, action]) => {
        if (value !== requiredValue) {
          action();
        }
      });
      this.updateCombined({ servoAngle: 0, camPan: 0, camTilt: 0, speed: 0 });
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
      const nextAngle = Math.trunc(
        constrainServoCommand(useRobotStore().data.cam_tilt_servo, angle),
      );
      this.sendMessage({ action: "setCamTiltAngle", payload: nextAngle });
    },

    setDirServoAngle(servoAngle: number) {
      const nextAngle = constrainServoCommand(
        useRobotStore().data.steering_servo,
        servoAngle,
      );
      this.requestedServoAngle = nextAngle;
      this.sendMessage({ action: "setServoDirAngle", payload: nextAngle });
    },

    setCamPanAngle(servoAngle: number): void {
      const nextAngle = Math.trunc(
        constrainServoCommand(useRobotStore().data.cam_pan_servo, servoAngle),
      );
      this.sendMessage({ action: "setCamPanAngle", payload: nextAngle });
    },

    updateCombined(payload: UpdateCombinedPayload): void {
      if (payload.speed === 0 || payload.direction === 0) {
        this.stop();
      }
      this.sendMessage({ action: "update", payload });
    },

    move(speed: number, direction: number) {
      const robotStore = useRobotStore();
      speed = constrain(0, Math.min(this.maxSpeed, robotStore.maxSpeed), speed);
      if (!this.model?.connected) {
        this.clearMotionHeartbeat();
        this.requestedSpeed = 0;
        this.requestedDirection = 0;
        return;
      }
      this.requestedSpeed = speed;
      this.requestedDirection = direction;
      this.sendRequestedMotion();
      if (speed > 0 && direction !== 0) {
        this.startMotionHeartbeat();
      } else {
        this.clearMotionHeartbeat();
      }
    },

    sendRequestedMotion() {
      this.sendMessage({
        action: "move",
        payload: {
          direction: this.requestedDirection,
          speed: this.requestedSpeed,
        },
      });
    },

    startMotionHeartbeat() {
      if (this.motionHeartbeat) {
        return;
      }
      this.motionHeartbeat = setInterval(() => {
        if (!this.model?.connected) {
          this.clearMotionHeartbeat();
          return;
        }
        this.sendRequestedMotion();
      }, 100);
    },

    clearMotionHeartbeat() {
      if (this.motionHeartbeat) {
        clearInterval(this.motionHeartbeat);
        this.motionHeartbeat = null;
      }
    },

    forward(speed: number) {
      this.move(speed, 1);
    },

    backward(speed: number) {
      this.move(speed, -1);
    },

    // commands
    accelerate() {
      const appliedSpeed = this.direction === 1 ? this.speed : 0;
      const requestedSpeed =
        this.requestedDirection === 1 ? this.requestedSpeed : 0;
      this.forward(
        Math.min(
          Math.max(appliedSpeed, requestedSpeed) + ACCELERATION,
          this.maxSpeed,
        ),
      );
    },

    decelerate() {
      const appliedSpeed = this.direction === -1 ? this.speed : 0;
      const requestedSpeed =
        this.requestedDirection === -1 ? this.requestedSpeed : 0;
      const nextSpeed = Math.min(
        Math.max(appliedSpeed, requestedSpeed) + ACCELERATION,
        this.maxSpeed,
      );
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
      this.clearMotionHeartbeat();
      this.requestedSpeed = 0;
      this.requestedDirection = 0;
      this.sendMessage({ action: "stop" });
    },
    emergencyStop(reason = "operator request") {
      this.clearMotionHeartbeat();
      this.requestedSpeed = 0;
      this.requestedDirection = 0;
      this.sendMessage({ action: "emergencyStop", payload: reason });
    },
    clearEmergencyStop() {
      this.sendMessage({ action: "clearEmergencyStop" });
    },
    clearMotionFault() {
      this.sendMessage({ action: "clearMotionFault" });
    },
    setRobotMode(mode: Exclude<RobotMode, "legacy" | "estop" | "fault">) {
      this.sendMessage({ action: "setRobotMode", payload: mode });
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
      const robotStore = useRobotStore();
      this.setCamTiltAngle(
        this.camTilt + robotStore.data.cam_tilt_servo.inc_step,
      );
    },

    decreaseCamTilt() {
      const robotStore = useRobotStore();
      this.setCamTiltAngle(
        this.camTilt + robotStore.data.cam_tilt_servo.dec_step,
      );
    },

    increaseCamPan() {
      const robotStore = useRobotStore();
      this.setCamPanAngle(this.camPan + robotStore.data.cam_pan_servo.inc_step);
    },

    resetCamPan() {
      this.setCamPanAngle(0);
    },

    decreaseCamPan() {
      const robotStore = useRobotStore();
      this.setCamPanAngle(this.camPan + robotStore.data.cam_pan_servo.dec_step);
    },

    resetCameraRotate() {
      this.updateCombined({ camTilt: 0, camPan: 0 });
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
      const currentAngle = this.requestedServoAngle ?? this.servoAngle;
      this.setDirServoAngle(
        currentAngle +
          (robotStore.data.steering_servo.dec_step ||
            robotStore.data.steering_servo.min_angle),
      );
    },
    right() {
      const robotStore = useRobotStore();
      const currentAngle = this.requestedServoAngle ?? this.servoAngle;
      this.setDirServoAngle(
        currentAngle +
          (robotStore.data.steering_servo.inc_step ||
            robotStore.data.steering_servo.max_angle),
      );
    },

    toggleCalibration() {
      const popupStore = usePopupStore();
      const messager = useMessagerStore();
      if (this.calibrationMode) {
        this.sendMessage({ action: "stopServoTuning" });
        messager.info(
          "Keyboard tuning stopped; save tuning to keep adjustments",
        );
      } else {
        this.stop();
        this.sendMessage({ action: "startServoTuning" });
        popupStore.isOpen = false;
      }
    },
    increaseCamPanCali() {
      this.sendMessage({
        action: isCalibrationStepReversed(useRobotStore().data.cam_pan_servo)
          ? "decreaseCamPanCali"
          : "increaseCamPanCali",
      });
    },
    decreaseCamPanCali() {
      this.sendMessage({
        action: isCalibrationStepReversed(useRobotStore().data.cam_pan_servo)
          ? "increaseCamPanCali"
          : "decreaseCamPanCali",
      });
    },
    increaseCamTiltCali() {
      this.sendMessage({
        action: isCalibrationStepReversed(useRobotStore().data.cam_tilt_servo)
          ? "decreaseCamTiltCali"
          : "increaseCamTiltCali",
      });
    },
    decreaseCamTiltCali() {
      this.sendMessage({
        action: isCalibrationStepReversed(useRobotStore().data.cam_tilt_servo)
          ? "increaseCamTiltCali"
          : "decreaseCamTiltCali",
      });
    },
    increaseServoDirCali() {
      this.sendMessage({
        action: isCalibrationStepReversed(useRobotStore().data.steering_servo)
          ? "decreaseServoDirCali"
          : "increaseServoDirCali",
      });
    },
    decreaseServoDirCali() {
      this.sendMessage({
        action: isCalibrationStepReversed(useRobotStore().data.steering_servo)
          ? "increaseServoDirCali"
          : "decreaseServoDirCali",
      });
    },
    reverseMotor(index: number) {
      this.sendMessage({ action: "reverseMotor", payload: index });
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
    updateServoDirCali(value: number) {
      this.sendMessage({ action: "updateServoDirCali", payload: value });
    },
    updateCamPanCali(value: number) {
      this.sendMessage({ action: "updateCamPanCali", payload: value });
    },
    updateCamTiltCali(value: number) {
      this.sendMessage({ action: "updateCamTiltCali", payload: value });
    },
    updateMotorCaliDir(index: number, value: number) {
      this.sendMessage({
        action: "updateMotorCaliDir",
        payload: { index, value },
      });
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
      batteryStore.fetchBatteryMetrics();
    },
    openShortcutsSettings() {
      const popupStore = usePopupStore();
      popupStore.tab = SettingsTab.KEYBINDINGS;
      popupStore.isOpen = true;
    },
    openGeneralSettings() {
      const popupStore = usePopupStore();
      popupStore.tab = popupStore.tab || SettingsTab.GENERAL;
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
