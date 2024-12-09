import type { ShallowRef } from "vue";
import { defineStore } from "pinia";
import axios from "axios";
import type { TreeNode } from "primevue/treenode";
import { useMessagerStore } from "@/features/messager";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";

export interface DetectionSettings {
  /**
   * The name or ID of the detection model to be used.
   */
  model: string | null;

  /**
   * The confidence threshold for detections (e.g., a value between 0 and 1).
   */
  confidence: number;

  /**
   * Indicates whether detection is active.
   */
  active: boolean;

  /**
   * The size of the image for detection (default is 640).
   */
  img_size: number;

  /**
   * A list of labels (e.g., object categories) to filter detections.
   */
  labels: string[] | null;
  /**
   * The maximum allowable time difference (in seconds) between the frame
   *  timestamp and the detection timestamp for overlay drawing to occur.
   */
  overlay_draw_threshold: number;
}

export interface DetectionResponse {
  detection_result: DetectionResult[];
  timestamp: number | null;
  loading: boolean;
}
export interface State extends DetectionResponse {
  data: DetectionSettings;
  loading: boolean;
  detectors: TreeNode[];
  connection: ShallowRef<WebSocketModel> | null;
  currentFrameTimestamp?: number;
}
export const defaultState: State = {
  loading: false,
  data: {
    active: false,
    confidence: 0.4,
    img_size: 640,
    model: null,
    labels: null,
    overlay_draw_threshold: 1,
  },
  detectors: [],
  detection_result: [],
  timestamp: null,
  connection: null,
};

export interface DetectionResult {
  bbox: [number, number, number, number];
  label: string;
  confidence: number;
}
export const msg = {
  retry: "Retrying object detection connection...",
  closing: "Closing object detection connection...",
  error: "Object detection connection error",
};

export const useStore = defineStore("detection-settings", {
  state: () => ({ ...defaultState }),
  getters: {
    connecting({ connection }) {
      return connection?.loading.value;
    },
    connected({ connection }) {
      return connection?.connected.value;
    },
  },
  actions: {
    async updateData(payload: DetectionSettings) {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        await axios.post<DetectionSettings>("/api/detection/settings", payload);
      } catch (error) {
        messager.handleError(error, `Error starting camera`);
      } finally {
        this.loading = false;
      }
      return this.data;
    },

    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const { data } = await axios.get<DetectionSettings>(
          "/api/detection/settings",
        );
        this.data = data;
      } catch (error) {
        messager.handleError(error, "Error fetching detection settings");
      } finally {
        this.loading = false;
      }
    },

    async fetchModels() {
      const messager = useMessagerStore();
      this.loading = true;
      try {
        const response = await axios.get<TreeNode[]>("/api/detection/models");
        this.detectors = response.data;
      } catch (error) {
        messager.handleError(error, "Error fetching detection models");
      } finally {
        this.loading = false;
      }
    },
    async toggleDetection() {
      await this.updateData({
        ...this.data,
        active: !this.data.active,
      });
    },
    initializeWebSocket() {
      const messager = useMessagerStore();
      const model = useWebSocket({
        url: "ws/object-detection",
        onMessage: (data: DetectionResponse) => {
          if (data.detection_result) {
            this.detection_result = data.detection_result;
            this.timestamp = data.timestamp;
          }
        },
        onOpen: () => {
          messager.remove((m) =>
            [msg.closing, msg.retry, msg.error].includes(m.text),
          );
        },
        onClose: () => {
          this.detection_result = [];
          messager.info(msg.closing);
        },
        onError: () => {
          if (this.data.active) {
            messager.error(msg.error);
          }
          this.detection_result = [];
        },
        isRetryable: () =>
          new Promise((res) => {
            res(!!this.data.active);
          }),
      });

      this.connection = model;
      this.connection.initWS();
    },
    cleanup() {
      this.connection?.cleanup();
      this.connection = null;
    },
    setCurrentFrameTimestamp(timestamp: number) {
      this.currentFrameTimestamp = timestamp;
    },
  },
});
