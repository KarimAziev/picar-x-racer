import type { ShallowRef } from "vue";
import { defineStore } from "pinia";
import {
  useImageStore,
  useSettingsStore,
  useBatteryStore,
  useDistanceStore,
  useCameraStore,
  useMusicStore,
  useStreamStore,
  useDetectionStore,
} from "@/features/settings/stores";
import { useMessagerStore } from "@/features/messager/store";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";
import { formatObjectDiff } from "@/util/obj";
import { startCase } from "@/util/str";

export interface StoreState {
  model: ShallowRef<WebSocketModel> | null;
}

const defaultState: StoreState = {
  model: null,
} as const;

export interface WSMessageData {
  type: string;
  payload: any;
}

export const useAppSyncStore = defineStore("syncer", {
  state: (): StoreState => ({ ...defaultState }),
  actions: {
    initializeWebSocket() {
      if (this.model?.connected || this.model?.loading) {
        return;
      }
      const messager = useMessagerStore();
      const settingsStore = useSettingsStore();
      const cameraStore = useCameraStore();
      const streamStore = useStreamStore();
      const detectionStore = useDetectionStore();
      const musicStore = useMusicStore();
      const imageStore = useImageStore();
      const batteryStore = useBatteryStore();
      const distanceStore = useDistanceStore();

      const handleMessage = (data: WSMessageData) => {
        if (!data) {
          return;
        }
        const { type, payload } = data;
        let msgPrefix: null | string = `${type}:`;
        let diffMsg: string | undefined;

        switch (type) {
          case "player":
            msgPrefix = null;
            musicStore.player = payload;
            break;
          case "music":
            musicStore.data = payload;
            break;
          case "volume": {
            diffMsg = `${payload}`;
            musicStore.volume = payload;
            break;
          }
          case "uploaded":
          case "removed": {
            const mediaType: string = payload.type;
            msgPrefix = `${startCase(type)} ${mediaType} file `;
            diffMsg = `${payload.file}`;
            const mediaTypeRefreshers: { [key: string]: Function } = {
              music: musicStore.fetchData,
              data: detectionStore.fetchModels,
              image: imageStore.fetchData,
            };
            if (mediaType && mediaTypeRefreshers[mediaType]) {
              mediaTypeRefreshers[mediaType]();
            }
            break;
          }
          case "battery": {
            diffMsg = `${payload}`;
            batteryStore.voltage = payload;
            break;
          }

          case "camera": {
            msgPrefix = "Camera: ";
            diffMsg = formatObjectDiff({ ...cameraStore.data }, payload);
            cameraStore.data = payload;
            break;
          }

          case "detection": {
            diffMsg = formatObjectDiff({ ...detectionStore.data }, payload);
            detectionStore.data = payload;
            break;
          }

          case "settings": {
            const currentData = { ...settingsStore.data };
            const nextData = { ...currentData, ...payload };

            diffMsg = formatObjectDiff(currentData, nextData);

            settingsStore.data = nextData;
            break;
          }

          case "distance":
            distanceStore.distance = payload;
            break;

          case "info":
            messager.info(payload, {
              immediately: true,
            });
            break;

          case "error":
            messager.error(payload, {
              immediately: true,
            });
            break;

          case "image":
            imageStore.data = payload;
            break;

          case "stream":
            streamStore.data = payload;
            break;
        }

        if (diffMsg) {
          messager.info(diffMsg, {
            immediately: true,
            title: msgPrefix ? msgPrefix : undefined,
          });
        }
      };

      this.model = useWebSocket({
        url: "ws/sync",
        onMessage: handleMessage,
        logPrefix: "sync",
      });
      this.model.initWS();
    },

    cleanup() {
      this.model?.cleanup();
      this.model = null;
    },

    sendMessage(message: any): void {
      this.model?.send(message);
    },
  },
});
