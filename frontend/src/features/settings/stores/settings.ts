import { defineStore } from "pinia";
import { cycleValue } from "@/util/cycleValue";
import { isObjectEquals, pick, setObjProp, getObjProp } from "@/util/obj";
import { retrieveError } from "@/util/error";

import { SettingsTab } from "@/features/settings/enums";
import { useMessagerStore, ShowMessageTypeProps } from "@/features/messager";
import { useStore as usePopupStore } from "@/features/settings/stores/popup";

import {
  useStore as useStreamStore,
  defaultState as defaultStreamState,
} from "@/features/settings/stores/stream";
import {
  defaultState as defaultCameraState,
  useStore as useCameraStore,
} from "@/features/settings/stores/camera";
import {
  useDetectionStore,
  defaultState as detectionDefaultState,
} from "@/features/detection";
import { useStore as useMusicStore, MusicMode } from "@/features/music";
import type { Settings, ToggleableKey } from "@/features/settings/interface";
import { appApi } from "@/api";

export interface State {
  loading?: boolean;
  loaded?: boolean;
  saving?: boolean;
  data: Settings;
  error?: string;
  retryTimer?: NodeJS.Timeout;
  retryCounter: number;
  text?: null | string;
  language?: null | string;
  inhibitKeyHandling: boolean;
}

export const defaultState: State = {
  data: {
    general: {
      robot_3d_view: true,
      speedometer_view: true,
      text_info_view: true,
      auto_download_photo: true,
      auto_download_video: true,
      virtual_mode: false,
      show_player: true,
      show_object_detection_settings: true,
      text_to_speech_input: true,
      show_battery_indicator: false,
      show_connections_indicator: true,
      show_auto_measure_distance_button: true,
      show_audio_stream_button: true,
      show_photo_capture_button: true,
      show_video_record_button: true,
      show_shutdown_reboot_button: true,
      show_fullscreen_button: true,
      show_avoid_obstacles_button: true,
      show_dark_theme_toggle: false,
    },
    keybindings: {},

    tts: {
      default_tts_language: "en",
      texts: [],
    },

    robot: {
      max_speed: 80,
      auto_measure_distance_mode: false,
      auto_measure_distance_delay_ms: 1000,
    },

    camera: { ...defaultCameraState.data },
    music: {
      order: [],
      mode: MusicMode.LOOP,
    },
    detection: { ...detectionDefaultState.data },
    stream: { ...defaultStreamState.data },
  },
  retryCounter: 0,
  text: null,
  language: null,
  inhibitKeyHandling: false,
};

export const useStore = defineStore("settings", {
  state: () => ({ ...defaultState }),
  getters: {
    detection({ data: { detection } }) {
      return detection;
    },

    generalSettings({ data }) {
      const cameraStore = useCameraStore();
      const streamStore = useStreamStore();
      const settingsData = pick(["general"], data);
      return {
        ...settingsData,
        camera: cameraStore.data,
        stream: streamStore.data,
      } as Partial<Settings>;
    },
    musicSettings({ data }) {
      const musicStore = useMusicStore();
      const settingsData = pick(["music"], data);
      return {
        music: {
          ...settingsData.music,
          mode: musicStore.player.mode,
        },
      } as Partial<Settings>;
    },
  },
  actions: {
    async fetchSettingsInitial() {
      const errText = "Couldn't load settings, retrying...";
      const messager = useMessagerStore();
      const streamStore = useStreamStore();

      if (this.retryTimer) {
        clearTimeout(this.retryTimer);
      }
      try {
        this.loading = true;
        const [response] = await Promise.all([
          appApi.get<Settings>("/api/settings"),
          streamStore.fetchEnhancers(),
        ]);
        this.data = response;
        this.error = undefined;
      } catch (error) {
        this.error = retrieveError(error).text;
        console.error("Error fetching settings:", error);
      } finally {
        this.loading = false;
        this.loaded = true;
      }
      if (this.error) {
        this.retryCounter += 1;
        this.loading = true;
        this.loaded = false;
        if (this.retryCounter % 2 === 0) {
          messager.remove((m) => m.text === errText);
          messager.error(errText);
        }

        this.retryTimer = setTimeout(async () => {
          await this.fetchSettingsInitial();
        }, 4000);
      } else {
        this.retryCounter = 0;
        messager.remove((m) => m.text === errText);
      }
    },
    getCurrentTabSettings(): Partial<Settings> | null {
      const popupStore = usePopupStore();
      const currentTab = popupStore.tab;
      const detectionStore = useDetectionStore();
      switch (currentTab) {
        case SettingsTab.GENERAL:
          return this.generalSettings;
        case SettingsTab.KEYBINDINGS:
          return { keybindings: this.data.keybindings };
        case SettingsTab.TTS:
          return { tts: this.data.tts };
        case SettingsTab.MODELS:
          return {
            detection: detectionStore.data,
          };
        case SettingsTab.MUSIC:
          return this.musicSettings;
        default:
          return null;
      }
    },
    isSaveButtonDisabled() {
      const popupStore = usePopupStore();
      const musicStore = useMusicStore();
      const currentTab = popupStore.tab;
      const detectionStore = useDetectionStore();
      switch (currentTab) {
        case SettingsTab.MODELS:
          return isObjectEquals(detectionStore.data, this.data.detection);
        case SettingsTab.MUSIC:
          return musicStore.player.mode === this.data.music.mode;
        default:
          return false;
      }
    },
    async saveSettings() {
      const data = this.getCurrentTabSettings();

      const messager = useMessagerStore();
      if (!data) {
        messager.error("Nothing to save");
        return;
      }
      await this.saveData(data);
    },

    async saveData(data: Partial<Settings>) {
      const messager = useMessagerStore();
      this.saving = true;
      try {
        await appApi.post("/api/settings", data);
        messager.info("Settings saved");
      } catch (error) {
        messager.handleError(error, "Error saving settings");
      } finally {
        this.saving = false;
      }
    },

    toggleSettingsProp(
      prop: ToggleableKey,
      showMsg?: boolean,
      msgParams?: ShowMessageTypeProps | string,
    ) {
      const messager = useMessagerStore();
      const currVal = getObjProp(prop, this.data);

      const nextValue = !currVal;
      setObjProp(this.data, prop, nextValue);

      if (showMsg) {
        messager.info(`${prop}: ${nextValue}`, msgParams);
      }
      return nextValue;
    },
    async speakText(text: string, language?: string) {
      const messager = useMessagerStore();
      try {
        await appApi.post(`/api/tts/speak`, {
          text: text,
          lang: language,
        });
      } catch (error) {
        messager.handleError(error);
      }
    },
    cycleText(direction: number) {
      const messager = useMessagerStore();
      if (!this.text) {
        const item =
          this.data.tts.texts.find((item) => item.default) ||
          this.data.tts.texts[0];
        this.text = item.text;
        this.language = item.language;
        return;
      }
      const nextTrack = cycleValue(
        (v) => v.text === this.text,
        this.data.tts.texts,
        direction,
      );
      if (!nextTrack) {
        messager.error("No text");
        return;
      }

      this.text = nextTrack.text;
      this.language = nextTrack.language;
      const keybindings = this.data.keybindings.sayText;
      if (!keybindings || !keybindings.length) {
        return messager.info(
          `Current text to speak: ${this.text}. (Assign key to 'sayText' command to speak)`,
        );
      }
      const keyHint = keybindings.join(", ");
      messager.info(`Press '${keyHint}' to speak '${this.text}'`);
    },
    nextText() {
      this.cycleText(1);
    },
    prevText() {
      this.cycleText(-1);
    },
    async shutdown() {
      const messager = useMessagerStore();
      try {
        await appApi.get("/api/system/shutdown");
      } catch (error) {
        messager.handleError(error);
      }
    },
    async restart() {
      const messager = useMessagerStore();
      try {
        await appApi.get("/api/system/restart");
      } catch (error) {
        messager.handleError(error);
      }
    },
  },
});
