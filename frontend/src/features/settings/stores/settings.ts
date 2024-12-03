import { defineStore } from "pinia";
import axios from "axios";
import { cycleValue } from "@/util/cycleValue";
import { omit, isObjectEquals } from "@/util/obj";
import { retrieveError } from "@/util/error";
import type { ControllerActionName } from "@/features/controller/store";
import { defaultKeybindinds } from "@/features/settings/defaultKeybindings";
import { toggleableSettings } from "@/features/settings/config";
import { SettingsTab } from "@/features/settings/enums";
import {
  useMessagerStore,
  ShowMessageTypeProps,
} from "@/features/messager/store";
import { useStore as usePopupStore } from "@/features/settings/stores/popup";
import { useStore as useCalibrationStore } from "@/features/settings/stores/calibration";
import { useStore as useMusicStore } from "@/features/settings/stores/music";
import { useStore as useSoundStore } from "@/features/settings/stores/sounds";
import { useStore as useBatteryStore } from "@/features/settings/stores/battery";
import { useStore as useDetectionStore } from "@/features/settings/stores/detection";

export type ToggleableSettings = {
  [P in keyof typeof toggleableSettings]: boolean;
};

export interface TextItem {
  text: string;
  language: string;
  default?: boolean;
}

export interface CameraSettings {
  /**
   * The ID or name of the camera device.
   */
  device?: string;

  /**
   * The width of the camera frame in pixels.
   */
  width?: number;

  /**
   * The height of the camera frame in pixels.
   */
  height?: number;

  /**
   * The number of frames per second the camera should capture.
   */
  fps?: number;

  /**
   * The format for the pixels (e.g., 'RGB', 'GRAY').
   */
  pixel_format?: string;
}

export interface StreamSettings {
  /**
   * The format of the stream (e.g., '.jpg').
   */
  format: string;

  /**
   * The quality of the stream (0-100).
   */
  quality: number;

  /**
   * The enhancement mode for the stream, if any.
   */
  enhance_mode?: string | null;

  /**
   * Whether video recording is enabled.
   */
  video_record?: boolean;

  /**
   * Whether the frames per second (FPS) should be rendered.
   */
  render_fps?: boolean;
}

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
}

export interface CameraOpenRequestParams {
  camera: CameraSettings;
  detection: DetectionSettings;
  stream: StreamSettings;
}

export interface Settings
  extends Partial<ToggleableSettings>,
    CameraOpenRequestParams {
  default_sound: string;
  default_music?: string;
  default_tts_language: string;
  keybindings: Partial<Record<ControllerActionName, string[]>>;
  battery_full_voltage: number;
  auto_measure_distance_delay_ms: number;
  texts: TextItem[];
}

export interface State {
  loading?: boolean;
  loaded?: boolean;
  saving?: boolean;
  settings: Settings;
  error?: string;
  retryTimer?: NodeJS.Timeout;
  retryCounter: number;
  text?: null | string;
  language?: null | string;
  inhibitKeyHandling: boolean;
}

export const defaultState: State = {
  settings: {
    fullscreen: true,
    keybindings: {},
    default_sound: "",
    default_tts_language: "en",
    texts: [],
    battery_full_voltage: 8.4,
    auto_measure_distance_delay_ms: 1000,
    camera: {},
    detection: {
      active: false,
      confidence: 0.4,
      img_size: 640,
      model: null,
      labels: null,
    },
    stream: {
      format: ".jpg",
      quality: 100,
    },
  },
  retryCounter: 0,
  text: null,
  language: null,
  inhibitKeyHandling: false,
};

export const useStore = defineStore("settings", {
  state: () => ({ ...defaultState }),
  getters: {
    detection({ settings: { detection } }) {
      return detection;
    },
    tts({ settings: { texts, default_tts_language } }) {
      return {
        default_tts_language,
        texts: texts.filter((item) => !!item.text.length),
      };
    },
    keybindings({ settings: { keybindings } }) {
      return { keybindings };
    },

    generalSettings({ settings }) {
      const excludedKeys: (keyof Settings)[] = [
        "keybindings",
        "texts",
        "default_tts_language",
        "detection",
      ];
      return omit(excludedKeys, settings);
    },
  },

  actions: {
    async fetchSettings() {
      const messager = useMessagerStore();
      const musicStore = useMusicStore();
      try {
        this.loading = true;
        const response = await axios.get("/api/settings");
        const resData = response.data;

        const data = {
          ...this.settings,
          keybindings: { ...defaultKeybindinds },
          ...resData,
        };
        this.settings = data;
        musicStore.autoplay = this.settings.autoplay_music || false;
        this.error = undefined;
        messager.info("System status: OK");
      } catch (error) {
        this.error = retrieveError(error).text;
        messager.handleError(error, "Error fetching settings");
      } finally {
        this.loading = false;
      }
    },

    async fetchSettingsInitial() {
      const errText = "Couldn't load settings, retrying...";
      const messager = useMessagerStore();
      const calibrationStore = useCalibrationStore();
      const musicStore = useMusicStore();
      const soundStore = useSoundStore();
      const batteryStore = useBatteryStore();
      if (this.retryTimer) {
        clearTimeout(this.retryTimer);
      }
      try {
        this.loading = true;
        const response = await axios.get("/api/settings");

        const data = {
          ...this.settings,
          keybindings: { ...defaultKeybindinds },
          ...response.data,
        };
        this.settings = data;
        await Promise.all([
          calibrationStore.fetchData(),
          musicStore.fetchData(),
          musicStore.getCurrentStatus(),
          soundStore.fetchDefaultData(),
          soundStore.fetchData(),
          batteryStore.fetchBatteryStatus(),
        ]);
        musicStore.autoplay = this.settings.autoplay_music || false;
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
    getCurrentTabSettings() {
      const popupStore = usePopupStore();
      const currentTab = popupStore.tab;
      const detectionStore = useDetectionStore();
      switch (currentTab) {
        case SettingsTab.GENERAL:
          return this.generalSettings;
        case SettingsTab.KEYBINDINGS:
          return this.keybindings;
        case SettingsTab.TTS:
          return this.tts;
        case SettingsTab.MODELS:
          return detectionStore.data;
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
          return isObjectEquals(detectionStore.data, this.settings.detection);
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
      prop: keyof ToggleableSettings,
      showMsg?: boolean,
      msgParams?: ShowMessageTypeProps | string,
    ) {
      const messager = useMessagerStore();
      const nextValue = !this.settings[prop];
      this.settings[prop] = nextValue;
      if (showMsg) {
        messager.info(`${prop}: ${nextValue}`, msgParams);
      }
      return nextValue;
    },
    async speakText(text: string, language?: string) {
      const messager = useMessagerStore();
      try {
        const response = await axios.post(`/api/play-tts`, {
          text: text,
          lang: language,
        });
        const data = response.data;
        const msg = data.status ? `Speaking: ${text}` : "Not speaking";
        messager.info(msg);
      } catch (error) {
        messager.handleError(error);
      }
    },
    cycleText(direction: number) {
      const messager = useMessagerStore();
      if (!this.text) {
        const item =
          this.settings.texts.find((item) => item.default) ||
          this.settings.texts[0];
        this.text = item.text;
        this.language = item.language;
        messager.info(
          `Text to speech: ${this.text}, language: ${this.language}`,
        );
        return;
      }
      const nextTrack = cycleValue(
        (v) => v.text === this.text,
        this.settings.texts,
        direction,
      );
      if (!nextTrack) {
        messager.error("No text");
        return;
      }

      this.text = nextTrack.text;
      this.language = nextTrack.language;
      messager.info(`Text to speech: ${this.text}, language: ${this.language}`);
    },
    nextText() {
      this.cycleText(1);
    },
    prevText() {
      this.cycleText(-1);
    },
  },
});
