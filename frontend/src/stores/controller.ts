import { defineStore } from "pinia";

const ACCELERATION = 10;
const CAM_PAN_MIN = -90;
const CAM_PAN_MAX = 90;
const CAM_TILT_MIN = -35;
const CAM_TILT_MAX = 65;
const SERVO_DIR_ANGLE_MIN = -30;
const SERVO_DIR_ANGLE_MAX = 30;

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
} as const;

export const useControllerStore = defineStore("controller", {
  state: (): StoreState => ({ ...defaultState }),
  actions: {
    initializeWebSocket(url: string) {
      this.url = url;

      this.websocket = new WebSocket(url);
      this.loading = true;
      this.websocket!.onopen = () => {
        this.loading = false;
        console.log(`WebSocket connection established with URL: ${url}`);
        this.connected = true;
        while (this.messageQueue.length > 0) {
          this.websocket!.send(this.messageQueue.shift()!);
        }
      };

      this.websocket.onmessage = (msg) => {
        let data;
        try {
          data = JSON.parse(msg.data);
          if (data) {
            this.distance = data?.distance;
          }
        } catch (error) {}
      };

      this.websocket.onerror = (error) => {
        console.error(`WebSocket error: ${error}`);
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
      if (this.reconnectedEnabled) {
        setTimeout(() => {
          console.log("Retrying WebSocket connection...");
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
      const curr = Math.max(20, this.maxSpeed - ACCELERATION);
      if (this.maxSpeed !== curr) {
        this.maxSpeed = curr;

        if (this.speed >= this.maxSpeed) {
          this.speed = Math.max(20, this.maxSpeed - 10);
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
      this.sendMessage({ action: "playMusic" });
    },

    playSound(): void {
      this.sendMessage({ action: "playSound" });
    },

    sayText(): void {
      this.sendMessage({ action: "sayText" });
    },

    getDistance(): void {
      this.sendMessage({ action: "getDistance" });
    },

    takePhoto(): void {
      this.sendMessage({ action: "takePhoto" });
    },
    setDirServoAngle(servoAngle: number) {
      const nextAngle = Math.min(
        Math.max(SERVO_DIR_ANGLE_MIN, servoAngle),
        SERVO_DIR_ANGLE_MAX,
      );
      this.sendMessage({ action: "setServo", angle: nextAngle });
      this.servoAngle = nextAngle;
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
