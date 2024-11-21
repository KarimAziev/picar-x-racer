import { useMessagerStore } from "@/features/messager/store";
import { makeWebsocketUrl } from "@/util/url";
import { defineStore } from "pinia";
import { useCameraStore } from "@/features/settings/stores";

export interface DetectionResult {
  bbox: [number, number, number, number];
  label: string;
  confidence: number;
}

export interface Detection {
  detection_result: DetectionResult[];
  timestamp: number | null;
  model: string | null;
  loading: boolean;
}
export const msg = {
  retry: "Retrying object detection connection...",
  closing: "Closing object detection connection...",
  error: "Object detection connection error",
};

export interface StoreState extends Detection {
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
   * The WebSocket message queue
   */
  messageQueue: string[];
  /**
   * The WebSocket URL
   */
  url: string;
  /**
   * Whether WebSocket is allowed to reconnect.
   */
  reconnectedEnabled?: boolean;
  currentFrameTimestamp?: number;
}

const defaultState: StoreState = {
  detection_result: [],
  connected: false,
  reconnectedEnabled: true,
  messageQueue: [],
  timestamp: null,
  loading: false,
  model: null,
  url: makeWebsocketUrl("ws/object-detection"),
} as const;

export const useDetectionStore = defineStore("detection", {
  state: (): StoreState => ({ ...defaultState }),
  actions: {
    initializeWebSocket() {
      const messager = useMessagerStore();

      this.websocket = new WebSocket(this.url);
      this.loading = true;
      this.websocket!.onopen = () => {
        this.loading = false;
        messager.remove((m) =>
          [msg.closing, msg.retry, msg.error].includes(m.text),
        );
        console.log(
          `Object detection connection established with URL: ${this.url}`,
        );
        this.connected = true;
        while (this.messageQueue.length > 0) {
          this.websocket!.send(this.messageQueue.shift()!);
        }
      };

      this.websocket.onmessage = (msgRaw) => {
        try {
          const data: Detection = JSON.parse(msgRaw.data);

          if (data.detection_result) {
            this.detection_result = data.detection_result;
            this.timestamp = data.timestamp;
            this.model = data.model;
          }
        } catch (error) {}
      };

      this.websocket.onerror = (error) => {
        console.error(`WebSocket error: ${error.type}`);
        messager.error(msg.error);
        this.detection_result = [];
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
    setCurrentFrameTimestamp(timestamp: number) {
      this.currentFrameTimestamp = timestamp;
    },
    async retryConnection() {
      const messager = useMessagerStore();
      const camStore = useCameraStore();
      if (this.reconnectedEnabled && !this.connected) {
        await camStore.fetchAllCameraSettings();
        if (camStore.data.video_feed_object_detection) {
          setTimeout(async () => {
            console.log(msg.retry);
            messager.info(msg.retry);
            this.initializeWebSocket();
          }, 5000);
        }
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
      messager.info(msg.closing);
      this.websocket?.close();
    },
    cleanup() {
      this.reconnectedEnabled = false;

      this.close();

      this.loading = false;
      this.messageQueue = [];
      this.detection_result = [];
      this.timestamp = this.timestamp;
      this.model = this.model;
    },
  },
});
