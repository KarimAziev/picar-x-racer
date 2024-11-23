import type { ShallowRef } from "vue";
import { useMessagerStore } from "@/features/messager/store";
import { defineStore } from "pinia";
import { useCameraStore } from "@/features/settings/stores";
import { ObjectDetectionParams } from "@/features/settings/stores/settings";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";

export interface DetectionResult {
  bbox: [number, number, number, number];
  label: string;
  confidence: number;
}

export interface Detection extends Partial<ObjectDetectionParams> {
  detection_result: DetectionResult[];
  timestamp: number | null;
  loading: boolean;
}
export const msg = {
  retry: "Retrying object detection connection...",
  closing: "Closing object detection connection...",
  error: "Object detection connection error",
};

export interface StoreState extends Detection {
  model: ShallowRef<WebSocketModel> | null;
  currentFrameTimestamp?: number;
}

const defaultState: StoreState = {
  detection_result: [],
  model: null,
  timestamp: null,
  loading: false,
} as const;

export const useDetectionStore = defineStore("detection", {
  state: (): StoreState => ({ ...defaultState }),
  getters: {
    connecting({ model }) {
      return model?.loading.value;
    },
    connected({ model }) {
      return model?.connected.value;
    },
  },
  actions: {
    initializeWebSocket() {
      const messager = useMessagerStore();
      const camStore = useCameraStore();
      const model = useWebSocket({
        url: "ws/object-detection",
        onMessage: (data: Detection) => {
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
          camStore
            .fetchAllCameraSettings()
            .then(() => !!camStore.data.video_feed_object_detection),
      });

      this.model = model;
      this.model.initWS();
    },
    cleanup() {
      this.model?.cleanup();
      this.model = null;
    },
    setCurrentFrameTimestamp(timestamp: number) {
      this.currentFrameTimestamp = timestamp;
    },
  },
});
