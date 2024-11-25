import type { ShallowRef } from "vue";
import { defineStore } from "pinia";
import axios from "axios";
import type { TreeNode } from "primevue/treenode";
import { useMessagerStore } from "@/features/messager/store";
import { DetectionSettings } from "@/features/settings/stores/settings";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";

export type LoadingFields = Partial<{
  [P in keyof DetectionSettings]: boolean;
}>;

export interface DetectionResponse {
  detection_result: DetectionResult[];
  timestamp: number | null;
  loading: boolean;
}
export interface State extends DetectionResponse {
  data: DetectionSettings;
  loading: boolean;
  detectors: TreeNode[];
  loadingData: LoadingFields;
  connection: ShallowRef<WebSocketModel> | null;
  currentFrameTimestamp?: number;
}
const defaultState: State = {
  loading: false,
  data: {
    active: false,
    confidence: 0.4,
    img_size: 640,
    model: null,
    labels: null,
  },
  detectors: [],
  detection_result: [],
  timestamp: null,
  connection: null,
  loadingData: {},
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
      console.log("saving PAYLOAD", payload);

      try {
        this.loading = true;

        Object.keys(payload).forEach((key) => {
          this.loadingData[key as keyof DetectionSettings] = true;
        });

        await axios.post<DetectionSettings>("/api/detection-settings", payload);
      } catch (error) {
        if (axios.isCancel(error)) {
          console.log("Request canceled:", error.message);
        } else {
          messager.handleError(error, `Error starting camera`);
        }
      } finally {
        this.loading = false;
        this.loadingData = {};
      }
      return this.data;
    },

    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const { data } = await axios.get<DetectionSettings>(
          "/api/detection-settings",
        );
        this.data = data;
      } catch (error) {
        messager.handleError(error, "Error fetching video feed settings");
      } finally {
        this.loading = false;
      }
    },

    async fetchModels() {
      const messager = useMessagerStore();
      this.loading = true;
      try {
        const response = await axios.get<TreeNode[]>("/api/detection-models");
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
          messager.error(msg.error);
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
