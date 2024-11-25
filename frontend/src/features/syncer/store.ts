import type { ShallowRef } from "vue";
import { defineStore } from "pinia";
import {
  useImageStore,
  useSettingsStore,
  useBatteryStore,
  useDistanceStore,
  useCameraStore,
  useMusicStore,
  useSoundStore,
  useStreamStore,
  useDetectionStore,
} from "@/features/settings/stores";
import { MethodsWithoutParams } from "@/util/ts-helpers";
import { useMessagerStore } from "@/features/messager/store";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";
import { formatObjectDiff } from "@/util/obj";

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
      const soundStore = useSoundStore();
      const batteryStore = useBatteryStore();
      const distanceStore = useDistanceStore();

      const handleMessage = (data: WSMessageData) => {
        if (!data) {
          return;
        }
        const { type, payload } = data;
        let diffMsg: string | undefined;

        switch (type) {
          case "music":
            musicStore.data = payload;
            break;
          case "image":
            imageStore.data = payload;
            break;
          case "sound":
            soundStore.data = payload;
            break;
          case "battery":
            batteryStore.voltage = payload;
            break;
          case "distance":
            distanceStore.distance = payload;
            break;
          case "camera":
            diffMsg = formatObjectDiff({ ...cameraStore.data }, payload);
            cameraStore.data = payload;
            break;
          case "stream":
            streamStore.data = payload;
            break;

          case "detection":
            diffMsg = formatObjectDiff({ ...detectionStore.data }, payload);
            detectionStore.data = payload;

            break;

          case "settings":
            settingsStore.settings = payload;
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
        }

        if (diffMsg) {
          messager.info(diffMsg, {
            immediately: true,
            title: `Updated ${type}: `,
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

export type ControllerState = Omit<
  ReturnType<typeof useAppSyncStore>,
  keyof ReturnType<typeof defineStore>
>;

export type ControllerActions = MethodsWithoutParams<ControllerState>;
export type ControllerActionName = keyof ControllerActions;
