import { defineStore } from "pinia";
import {
  useImageStore,
  useSettingsStore,
  usePopupStore,
  useBatteryStore,
} from "@/features/settings/stores";
import { MethodsWithoutParams } from "@/util/ts-helpers";
import { SettingsTab } from "@/features/settings/enums";
import { useMessagerStore } from "@/features/messager/store";
import { isNumber } from "@/util/guards";

const ACCELERATION = 10;
const CAM_PAN_MIN = -90;
const CAM_PAN_MAX = 90;
const CAM_TILT_MIN = -35;
const CAM_TILT_MAX = 65;
const SERVO_DIR_ANGLE_MIN = -30;
const SERVO_DIR_ANGLE_MAX = 30;
const MIN_SPEED = 10;

export type StoreState = {
  loading: boolean;
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
  maxSpeed: number;
  camPan: number;
  camTilt: number;
  connected: boolean;
  websocket?: WebSocket;
  messageQueue: string[];
  url?: string;
  reconnectedEnabled?: boolean;
  distance?: number;
  avoidObstacles: false;
};

const defaultState: StoreState = {
  speed: 0,
  direction: 0,
  servoAngle: 0,
  maxSpeed: 80,
  camPan: 0,
  camTilt: 0,
  messageQueue: [],
  connected: false,
  loading: false,
  url: "ws://" + window.location.hostname + ":8765",
  reconnectedEnabled: true,
  avoidObstacles: false,
} as const;

export const useControllerStore = defineStore("controller", {
  state: (): StoreState => ({ ...defaultState }),
  actions: {
    initializeWebSocket(url: string) {
      const messager = useMessagerStore();
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
          const type = data?.type;
          switch (type) {
            case "getDistance":
              const value = data.payload;
              const error = data.error;
              this.distance = data.error || value;
              if (error) {
                messager.error(error, "distance error");
              } else {
                messager.info(`${value.toFixed(2)} sm`, "distance");
              }

              break;
            case "takePhoto":
              messager.info("Recorded");
              const imageStore = useImageStore();
              if (data.payload) {
                imageStore.downloadFile(data.payload);
              } else if (data.error) {
                messager.error(`Couldn't take photo: ${data.error}`);
              }
              break;

            case "stop":
              this.direction = 0;
              this.speed = 0;
              break;

            case "move":
              const { direction, speed, servoAngle } = data.payload;
              this.direction =
                direction === "forward" ? 1 : direction === "backward" ? -1 : 0;
              if (isNumber(speed)) {
                this.speed = speed;
              }
              if (isNumber(servoAngle)) {
                this.servoAngle = servoAngle;
              }

              break;

            case "setServo":
              this.servoAngle = data.paylaod;
              break;

            case "setCamPanAngle":
              this.camPan = data.payload;
              break;

            case "setCamTiltAngle":
              this.camTilt = data.payload;
              break;

            case "avoidObstacles":
              this.avoidObstacles = data.payload;
              messager.info(`Avoid Obstacles: ${data.payload}`);
              break;

            default:
              if (data.error) {
                messager.error(data.error);
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
      const curr = Math.min(100, this.maxSpeed + ACCELERATION);
      if (this.maxSpeed !== curr) {
        this.maxSpeed = curr;
      }
    },

    decreaseMaxSpeed() {
      const curr = Math.max(MIN_SPEED, this.maxSpeed - ACCELERATION);

      if (this.maxSpeed !== curr) {
        this.maxSpeed = curr;

        if (this.speed >= this.maxSpeed) {
          this.speed = Math.max(MIN_SPEED, this.maxSpeed - ACCELERATION);
        }
      }
    },

    resetCamTilt() {
      this.setCamTiltAngle(0);
    },

    increaseCamTilt() {
      this.setCamTiltAngle(Math.min(this.camTilt + 5, CAM_TILT_MAX));
    },

    decreaseCamTilt() {
      this.setCamTiltAngle(Math.max(this.camTilt - 5, CAM_TILT_MIN));
    },

    increaseCamPan() {
      this.setCamPanAngle(Math.min(this.camPan + 5, CAM_PAN_MAX));
    },

    resetCamPan() {
      this.setCamPanAngle(0);
    },

    decreaseCamPan() {
      this.setCamPanAngle(Math.max(this.camPan - 5, CAM_PAN_MIN));
    },

    resetCameraRotate() {
      this.resetCamPan();
      this.resetCamTilt();
    },

    forward(speed: number) {
      if (this.speed !== speed || this.direction !== 1) {
        this.sendMessage({ action: "move", direction: "forward", speed });
      }

      this.direction = 1;
      this.speed = speed;
    },

    backward(speed: number) {
      if (this.speed !== speed || this.direction !== -1) {
        this.sendMessage({ action: "move", direction: "backward", speed });
      }

      this.direction = -1;
      this.speed = speed;
    },

    setDirServoAngle(servoAngle: number) {
      const nextAngle = Math.min(
        Math.max(SERVO_DIR_ANGLE_MIN, servoAngle),
        SERVO_DIR_ANGLE_MAX,
      );
      this.sendMessage({ action: "setServo", angle: nextAngle });
      this.servoAngle = nextAngle;
    },

    resetDirServoAngle(): void {
      this.setDirServoAngle(0);
    },

    setCamTiltAngle(servoAngle: number): void {
      const nextAngle = Math.min(
        Math.max(CAM_PAN_MIN, servoAngle),
        CAM_PAN_MAX,
      );
      this.sendMessage({ action: "setCamTiltAngle", angle: nextAngle });
      this.camTilt = nextAngle;
    },

    setCamPanAngle(servoAngle: number): void {
      const nextAngle = Math.min(
        Math.max(CAM_PAN_MIN, servoAngle),
        CAM_PAN_MAX,
      );
      this.sendMessage({ action: "setCamPanAngle", angle: nextAngle });
      this.camPan = nextAngle;
    },

    playMusic(): void {
      const messager = useMessagerStore();
      messager.info("Playback...");
      this.sendMessage({ action: "playMusic" });
    },

    playSound(): void {
      const messager = useMessagerStore();
      messager.info("Playback sound...");
      this.sendMessage({ action: "playSound" });
    },

    sayText(): void {
      const messager = useMessagerStore();
      messager.info("Talking..");
      this.sendMessage({ action: "sayText" });
    },

    getDistance(): void {
      const messager = useMessagerStore();
      messager.info("Distance measure...");
      this.sendMessage({ action: "getDistance" });
    },

    takePhoto(): void {
      const messager = useMessagerStore();
      messager.info("Recording photo...");
      this.sendMessage({ action: "takePhoto" });
    },

    left() {
      this.setDirServoAngle(-30);
    },
    right() {
      this.setDirServoAngle(30);
    },
    getBatteryVoltage() {
      const batteryStore = useBatteryStore();
      batteryStore.fetchBatteryStatus();
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
    toggleAvoidObstaclesMode() {
      this.sendMessage({ action: "avoidObstacles" });
    },
    toggleDrawFPS() {
      this.sendMessage({ action: "drawFPS" });
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
    increaseQuality() {
      const settingsStore = useSettingsStore();
      settingsStore.increaseQuality();
    },
    decreaseQuality() {
      const settingsStore = useSettingsStore();
      settingsStore.decreaseQuality();
    },

    cleanup() {
      this.reconnectedEnabled = false;

      this.stop();
      this.resetDirServoAngle();
      this.resetCameraRotate();
      this.websocket?.close();

      this.loading = false;
      this.speed = 0;
      this.websocket = undefined;
      this.messageQueue = [];
    },
  },
});

export type ControllerState = Omit<
  ReturnType<typeof useControllerStore>,
  keyof ReturnType<typeof defineStore>
>;

export type ControllerActions = MethodsWithoutParams<ControllerState>;
export type ControllerActionName = keyof ControllerActions;
