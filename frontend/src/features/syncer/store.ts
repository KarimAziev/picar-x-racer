import type { ShallowRef } from "vue";
import { defineStore } from "pinia";
import { useWebSocket, WebSocketModel } from "@/composables/useWebsocket";
import { formatObjectDiff, groupWith, isObjectShallowEquals } from "@/util/obj";
import { startCase } from "@/util/str";
import {
  useSettingsStore,
  useBatteryStore,
  useDistanceStore,
  useCameraStore,
  useStreamStore,
  usePopupStore,
} from "@/features/settings/stores";
import { useMessagerStore } from "@/features/messager";
import type { MessageItemParams } from "@/features/messager";
import { isPlainObject } from "@/util/guards";
import {
  useImageStore,
  useVideoStore,
  useDetectionDataStore,
  useDataStore,
  useMusicFileStore,
} from "@/features/files/stores";
import { SettingsTab } from "@/features/settings/enums";
import { useDetectionStore } from "@/features/detection";
import { useMusicStore } from "@/features/music";

export interface StoreState {
  model: ShallowRef<WebSocketModel> | null;
  active_connections: number;
}

const defaultState: StoreState = {
  model: null,
  active_connections: 0,
} as const;

export interface WSMessageData {
  type: string;
  payload: any;
  message?: string | MessageItemParams;
}

export const useStore = defineStore("syncer", {
  state: (): StoreState => ({ ...defaultState }),
  actions: {
    initializeWebSocket() {
      if (this.model?.connected || this.model?.loading) {
        return;
      }
      const messager = useMessagerStore();
      const popupStore = usePopupStore();
      const musicFileStore = useMusicFileStore();
      const settingsStore = useSettingsStore();
      const cameraStore = useCameraStore();
      const streamStore = useStreamStore();
      const detectionStore = useDetectionStore();
      const musicStore = useMusicStore();
      const detectionDataStore = useDetectionDataStore();
      const dataTableStore = useDataStore();
      const imageStore = useImageStore();
      const batteryStore = useBatteryStore();
      const distanceStore = useDistanceStore();
      const videoStore = useVideoStore();

      const handleMessage = (data: WSMessageData) => {
        if (!data) {
          return;
        }
        const { type, payload, message } = data;
        let msgPrefix: null | string =
          `${settingsStore.loaded ? "Updated " : ""} ${type}`.trim();
        let diffMsg: string | undefined;

        switch (type) {
          case "player": {
            msgPrefix = null;
            const inhibitSync =
              musicStore.inhibitPlayerSync &&
              musicStore.player.track === payload.track;

            if (
              !inhibitSync &&
              !isObjectShallowEquals(musicStore.player, payload)
            ) {
              musicStore.player = payload;
            }
            break;
          }
          case "music": {
            musicStore.data = payload;
            break;
          }

          case "camera_error": {
            cameraStore.error = payload;
            break;
          }
          case "volume": {
            diffMsg = `${payload}`;
            musicStore.volume = payload;
            break;
          }
          case "active_connections": {
            this.active_connections = payload;
            break;
          }
          case "uploaded":
          case "moved":
          case "created":
          case "renamed":
          case "removed": {
            const dataRefresher = () => {
              if (popupStore.isOpen && popupStore.tab === SettingsTab.MODELS) {
                dataTableStore.fetchData();
              }
              return detectionDataStore.fetchData();
            };
            const mediaTypeRefreshers: { [key: string]: () => Promise<any> } = {
              music: async () => {
                if (popupStore.isOpen) {
                  await musicFileStore.fetchData();
                  await musicStore.fetchData();
                }
              },
              data: dataRefresher,
              image: imageStore.fetchData,
              video: videoStore.fetchData,
            };
            const items: { type: string; file: string; msg?: string }[] =
              payload;
            const groupped = groupWith(
              "type",
              (item) => item.msg || item.file,
              items,
            );

            Object.entries(groupped).forEach(([mediaType, msgs]) => {
              const len = msgs.length;
              const prefix = `${startCase(type)} ${len} file${len === 1 ? "" : "s"}`;
              const msg =
                `${prefix} ${msgs.length < 2 ? msgs.join(", ") : ""}`.trim();
              messager.info(msg);

              mediaTypeRefreshers[mediaType]();
            });
            break;
          }
          case "stream": {
            diffMsg = formatObjectDiff(streamStore.data, payload);
            if (diffMsg) {
              streamStore.data = payload;
            }

            break;
          }
          case "battery": {
            batteryStore.voltage = payload.voltage;
            batteryStore.percentage = payload.percentage;
            break;
          }

          case "video_record_error": {
            if (streamStore.is_record_initiator) {
              streamStore.is_record_initiator = false;
            }
            messager.error(payload, {
              immediately: true,
            });
            break;
          }

          case "video_record_end": {
            videoStore.fetchData();
            if (
              streamStore.is_record_initiator &&
              settingsStore.data.general.auto_download_video
            ) {
              videoStore.downloadFile(payload);
            }
            if (streamStore.is_record_initiator) {
              streamStore.is_record_initiator = false;
            }

            break;
          }

          case "camera": {
            diffMsg = formatObjectDiff({ ...cameraStore.data }, payload);
            cameraStore.data = payload;
            break;
          }

          case "detection-loading": {
            detectionStore.loading = payload;
            break;
          }

          case "detection": {
            if (!message) {
              diffMsg = formatObjectDiff({ ...detectionStore.data }, payload);
            }

            detectionStore.data = payload;
            break;
          }

          case "settings": {
            const currentData = { ...settingsStore.data };
            const nextData = { ...currentData, ...payload };
            if (!message) {
              diffMsg = formatObjectDiff(currentData, nextData);
            }

            settingsStore.data = nextData;
            break;
          }

          case "distance": {
            distanceStore.distance = payload;
            break;
          }

          case "info": {
            messager.info(payload, {
              immediately: true,
            });
            break;
          }

          case "error": {
            messager.error(payload, {
              immediately: true,
            });
            break;
          }

          case "warning": {
            messager.warning(payload, {
              immediately: true,
            });
            break;
          }

          case "image": {
            imageStore.data = payload;
            break;
          }
        }

        if (isPlainObject(message)) {
          messager[message.type || "info"](message.text, message);
        } else if (message) {
          messager.info(message);
        } else if (diffMsg) {
          messager.info(diffMsg, {
            title: msgPrefix ? msgPrefix : undefined,
          });
        }
      };

      this.model = useWebSocket({
        url: "api/ws/sync",
        onMessage: handleMessage,
        onOpen: async () => {
          await settingsStore.fetchSettingsInitial();
        },
        onClose: () => {
          musicStore.isStreaming = false;
          musicStore.player.is_playing = false;
          detectionStore.data = {
            ...detectionStore.data,
            active: false,
          };
        },
        logPrefix: "sync",
        isRetryable: () =>
          new Promise((res) => {
            res(true);
          }),
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
