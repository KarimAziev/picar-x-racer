import { defineStore } from "pinia";
import {
  useImageStore,
  useSettingsStore,
  usePopupStore,
  useBatteryStore,
  useCalibrationStore,
  useDistanceStore,
  useCameraStore,
} from "@/features/settings/stores";
import { MethodsWithoutParams } from "@/util/ts-helpers";
import { SettingsTab } from "@/features/settings/enums";
import { useMessagerStore } from "@/features/messager/store";
import { isNumber, isPlainObject, isString } from "@/util/guards";
import { constrain } from "@/util/constrain";
import {
  playMusic,
  playSound,
  playTTS,
  takePhoto,
} from "@/features/controller/api";

const ACCELERATION = 10;
const CAM_PAN_MIN = -90;
const CAM_PAN_MAX = 90;
const CAM_TILT_MIN = -35;
const CAM_TILT_MAX = 65;
const SERVO_DIR_ANGLE_MIN = -30;
const SERVO_DIR_ANGLE_MAX = 30;
const MIN_SPEED = 10;
const MAX_SPEED = 100;

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
  /**
   * Whether the WebSocket is loading.
   */
  loading: boolean;
  /**
   * Whether the WebSocket connection is opened.
   */
  connected: boolean;
  /**
   * Current WebSocket instance
   */
  websocket?: WebSocket;
  /**
   * The WebSocket messages queue
   */
  messageQueue: string[];
  /**
   * The WebSocket URL
   */
  url?: string;
  /**
   * Whether WebSocket is allowed to reconnect.
   */
  reconnectedEnabled?: boolean;
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
  connected: false,
  reconnectedEnabled: true,
  messageQueue: [],
  loading: false,
  url: "ws://" + window.location.hostname + ":8765",
} as const;

export const useControllerStore = defineStore("controller", {
  state: (): StoreState => ({ ...defaultState }),
  actions: {
    initializeWebSocket(url: string) {
      const messager = useMessagerStore();
      const distanceStore = useDistanceStore();
      const calibrationStore = useCalibrationStore();
      this.url = url;

      this.websocket = new WebSocket(url);
      this.loading = true;
      this.websocket!.onopen = () => {
        this.loading = false;
        console.log(`WebSocket connection established with URL: ${url}`);
        messager.info("Connection status: Open");
        this.connected = true;
        while (this.messageQueue.length > 0) {
          this.websocket!.send(this.messageQueue.shift()!);
        }
      };

      this.websocket.onmessage = (msg) => {
        let data;
        try {
          data = JSON.parse(msg.data);
          if (!isPlainObject(data)) {
            return;
          }
          const { type, payload, error } = data;

          switch (type) {
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
                  } else if (
                    k in modes &&
                    (value === false || value === true)
                  ) {
                    this[k as keyof typeof modes] = value as boolean;
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
        } catch (error) {}
      };

      this.websocket.onerror = (error) => {
        console.error(`WebSocket error: ${error.type}`);
        messager.error("WebSocket error");
        this.loading = false;
        this.connected = false;
      };

      this.websocket.onclose = () => {
        console.log("WebSocket connection closed");

        this.connected = false;
        this.loading = false;
        this.retryConnection();
      };
    },

    retryConnection() {
      const messager = useMessagerStore();
      if (this.reconnectedEnabled && !this.connected) {
        setTimeout(() => {
          console.log("Retrying WebSocket connection...");
          messager.info("Retrying connection...");
          if (this.url) {
            this.initializeWebSocket(this.url);
          }
        }, 5000);
      }
    },

    sendMessage(message: any): void {
      const msgString = JSON.stringify(message);
      if (this.connected) {
        this.websocket!.send(msgString);
      } else {
        this.messageQueue.push(msgString);
      }
    },

    close() {
      const messager = useMessagerStore();
      messager.info("Closing connection...");
      this.websocket?.close();
    },
    cleanup() {
      this.reconnectedEnabled = false;

      this.stop();
      this.resetDirServoAngle();
      this.resetCameraRotate();
      this.close();

      this.loading = false;
      this.speed = 0;
      this.messageQueue = [];
    },
    // command workers
    setMaxSpeed(value: number) {
      const newValue = constrain(MIN_SPEED, MAX_SPEED, value);
      if (newValue !== this.maxSpeed) {
        this.maxSpeed = newValue;
      }
      if (this.speed >= newValue) {
        this.speed = constrain(MIN_SPEED, newValue, newValue - ACCELERATION);
      }
    },
    setCamTiltAngle(angle: number): void {
      const nextAngle = constrain(CAM_TILT_MIN, CAM_TILT_MAX, angle);
      this.sendMessage({ action: "setCamTiltAngle", payload: nextAngle });
      this.camTilt = nextAngle;
    },

    setCamPanAngle(servoAngle: number): void {
      const nextAngle = constrain(CAM_PAN_MIN, CAM_PAN_MAX, servoAngle);
      this.sendMessage({ action: "setCamPanAngle", payload: nextAngle });
      this.camPan = nextAngle;
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

      this.direction = direction;
      this.speed = speed;
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
      this.servoAngle = nextAngle;
    },
    // commands
    accelerate() {
      this.forward(Math.min(this.speed + ACCELERATION, this.maxSpeed));
    },

    decelerate() {
      const nextSpeed = Math.min(this.speed + ACCELERATION, this.maxSpeed);
      this.backward(nextSpeed);
    },

    slowdown() {
      if (this.speed > 0) {
        this.speed = Math.max(this.speed - 5, 0);
      }
      if (this.speed === 0 && this.direction !== 0) {
        this.stop();
        this.direction = 0;
      } else if (this.direction === 1) {
        this.forward(this.speed);
      } else if (this.direction === -1) {
        this.backward(this.speed);
      }
    },
    stop() {
      this.sendMessage({ action: "stop" });
      this.direction = 0;
      this.speed = 0;
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

    async playMusic() {
      const messager = useMessagerStore();
      const settingsStore = useSettingsStore();
      const name = settingsStore.settings.default_music;
      if (name) {
        try {
          const response = await playMusic(name);
          const data = response.data;
          const msg = data.playing ? `Playing ${name}` : "Stoped playing";
          messager.info(msg);
        } catch (error) {
          messager.handleError(error);
        }
      }
    },

    async playSound() {
      const messager = useMessagerStore();
      const settingsStore = useSettingsStore();
      const name = settingsStore.settings.default_sound;
      if (name) {
        try {
          const response = await playSound(name);
          const data = response.data;
          const msg = data.playing ? `Playing ${name}` : "Stoped playing";
          messager.info(msg);
        } catch (error) {
          messager.handleError(error);
        }
      }
    },

    async sayText() {
      const messager = useMessagerStore();
      const settingsStore = useSettingsStore();
      const text = settingsStore.settings.default_text;
      const lang = settingsStore.settings.default_language;
      if (text) {
        try {
          const response = await playTTS(text, lang);
          const data = response.data;
          const msg = data.status ? `Speaking: ${text}` : "Not speaking";
          messager.info(msg);
        } catch (error) {
          messager.handleError(error);
        }
      }
    },

    async getDistance() {
      const distanceStore = useDistanceStore();
      await distanceStore.fetchDistance();
    },

    async takePhoto() {
      const messager = useMessagerStore();
      const imageStore = useImageStore();
      const settingsStore = useSettingsStore();
      try {
        const response = await takePhoto();
        const file = response.data.file;
        if (file && settingsStore.settings.auto_download_photo) {
          await imageStore.downloadFile(file);
        }
      } catch (error) {
        messager.handleError(error);
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
        /**
         * popupStore.tab = SettingsTab.CALIBRATION;
         * popupStore.isOpen = true;
         */
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
    increaseQuality() {
      const settingsStore = useSettingsStore();
      settingsStore.increaseQuality();
    },
    decreaseQuality() {
      const settingsStore = useSettingsStore();
      settingsStore.decreaseQuality();
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
    toggleFullscreen() {
      const settingsStore = useSettingsStore();
      settingsStore.toggleSettingsProp("fullscreen");
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
  },
});

export type ControllerState = Omit<
  ReturnType<typeof useControllerStore>,
  keyof ReturnType<typeof defineStore>
>;

export type ControllerActions = MethodsWithoutParams<ControllerState>;
export type ControllerActionName = keyof ControllerActions;
