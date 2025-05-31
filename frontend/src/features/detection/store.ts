import type { ShallowRef } from "vue";
import { defineStore } from "pinia";
import type { TreeNode } from "primevue/treenode";
import { useMessagerStore } from "@/features/messager";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";
import {
  DetectionSettings,
  DetectionResponse,
} from "@/features/detection/interface";
import { OverlayStyle } from "@/features/detection/enums";
import { appApi } from "@/api";

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
    overlay_style: OverlayStyle.BOX,
  },
  detectors: [],
  detection_result: [],
  timestamp: null,
  connection: null,
};

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
        await appApi.post<DetectionSettings>(
          "/api/detection/settings",
          payload,
        );
      } catch (error) {
        messager.handleError(error);
      } finally {
      }
      return this.data;
    },

    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const data = await appApi.get<DetectionSettings>(
          "/api/detection/settings",
        );
        this.data = data;
      } catch (error) {
        messager.handleError(error, "Error fetching detection settings");
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
        url: "api/ws/object-detection",
        onMessage: (data: DetectionResponse) => {
          if (data.detection_result) {
            this.detection_result = data.detection_result;
            this.timestamp = data.timestamp;
          }
        },
        onOpen: () => {
          messager.remove((m) => [msg.retry, msg.error].includes(m.text));
        },
        onClose: () => {
          this.detection_result = [];
        },
        onError: () => {
          if (this.data.active) {
            messager.error(msg.error);
          }
          this.detection_result = [];
        },
        isRetryable: () =>
          new Promise((res) => {
            res(this.data.active);
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
