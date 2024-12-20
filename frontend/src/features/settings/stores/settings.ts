import axios from "axios";
import { defineStore } from "pinia";
import { cycleValue } from "@/util/cycleValue";
import { isObjectEquals, pick, setObjProp, getObjProp } from "@/util/obj";
import { retrieveError } from "@/util/error";

import { SettingsTab } from "@/features/settings/enums";
import { useMessagerStore, ShowMessageTypeProps } from "@/features/messager";
import { useStore as usePopupStore } from "@/features/settings/stores/popup";
import { useStore as useCalibrationStore } from "@/features/settings/stores/calibration";
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

export interface TextItem {
  text: string;
  language: string;
  default?: boolean;
}

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
      show_battery_indicator: true,
      show_connections_indicator: true,
      show_auto_measure_distance_button: true,
      show_audio_stream_button: true,
      show_photo_capture_button: true,
      show_video_record_button: true,
      show_shutdown_reboot_button: true,
    },
    keybindings: {},

    tts: {
      default_tts_language: "en",
      texts: [],
    },
    battery: {
      full_voltage: 8.4,
      warn_voltage: 7.15,
      danger_voltage: 6.5,
      min_voltage: 6.0,
      auto_measure_seconds: 60,
      cache_seconds: 2,
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
      const musicStore = useMusicStore();
      const cameraStore = useCameraStore();
      const streamStore = useStreamStore();
      const settingsData = pick(["general", "robot", "battery", "music"], data);
      return {
        ...settingsData,
        camera: cameraStore.data,
        stream: streamStore.data,
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
      const calibrationStore = useCalibrationStore();
      const musicStore = useMusicStore();
      const streamStore = useStreamStore();
      if (this.retryTimer) {
        clearTimeout(this.retryTimer);
      }
      try {
        this.loading = true;
        const [response] = await Promise.all([
          axios.get<Settings>("/api/settings"),
          calibrationStore.fetchData(),
          musicStore.fetchData(),
          streamStore.fetchEnhancers(),
        ]);
        this.data = response.data;
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
        default:
          return null;
      }
    },
    isSaveButtonDisabled() {
      const popupStore = usePopupStore();
      const currentTab = popupStore.tab;
      const detectionStore = useDetectionStore();
      switch (currentTab) {
        case SettingsTab.MODELS:
          return isObjectEquals(detectionStore.data, this.data.detection);
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
        await axios.post("/api/settings", data);
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
        await axios.post(`/api/tts/speak`, {
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
        await axios.get("/api/system/shutdown");
      } catch (error) {
        messager.handleError(error);
      }
    },
    async restart() {
      const messager = useMessagerStore();
      try {
        await axios.get("/api/system/restart");
      } catch (error) {
        messager.handleError(error);
      }
    },
  },
});
