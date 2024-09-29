import { defineStore } from "pinia";
import axios from "axios";
import { defaultKeybindinds } from "@/features/settings/defaultKeybindings";
import {
  useMessagerStore,
  ShowMessageTypeProps,
} from "@/features/messager/store";
import { isNumber } from "@/util/guards";
import { toggleableSettings } from "@/features/settings/config";
import { SettingsTab } from "@/features/settings/enums";
import { useStore as usePopupStore } from "@/features/settings/stores/popup";
import { useStore as useCalibrationStore } from "@/features/settings/stores/calibration";
import { omit } from "@/util/obj";
import type { ControllerActionName } from "@/features/controller/store";
import { retrieveError } from "@/util/error";
import { useStore as useMusicStore } from "@/features/settings/stores/music";
import { useStore as useSoundStore } from "@/features/settings/stores/sounds";
import { cycleValue } from "@/util/cycleValue";
import { useStore as useBatteryStore } from "@/features/settings/stores/battery";

export type ToggleableSettings = {
  [P in keyof typeof toggleableSettings]: boolean;
};

export interface TextItem {
  text: string;
  language: string;
  default?: boolean;
}

export interface CameraOpenRequestParams {
  video_feed_fps?: number;
  video_feed_format?: string;
  video_feed_enhance_mode: string | null;
  video_feed_detect_mode: string | null;
  video_feed_quality?: number;
  video_feed_height?: number;
  video_feed_width?: number;
  video_feed_confidence?: number;
}

export interface Settings
  extends Partial<ToggleableSettings>,
    CameraOpenRequestParams {
  default_sound: string;
  default_music?: string;
  keybindings: Partial<Record<ControllerActionName, string[]>>;
  battery_full_voltage: number;
  auto_measure_distance_delay_ms: number;
  video_feed_quality: number;
  texts: TextItem[];
}

export interface State {
  loading?: boolean;
  loaded?: boolean;
  saving?: boolean;
  settings: Settings;
  dimensions: { width: number; height: number };
  error?: string;
  retryTimer?: NodeJS.Timeout;
  retryCounter: number;
  text?: null | string;
  language?: null | string;
  inhibitKeyHandling: boolean;
}

const defaultState: State = {
  settings: {
    fullscreen: true,
    keybindings: {},
    default_sound: "",
    texts: [],
    battery_full_voltage: 8.4,
    auto_measure_distance_delay_ms: 1000,
    video_feed_quality: 100,
    video_feed_fps: 30,
    video_feed_format: ".jpg",
    video_feed_detect_mode: null,
    video_feed_enhance_mode: null,
  },
  dimensions: { width: 640, height: 480 },
  retryCounter: 0,
  text: null,
  language: null,
  inhibitKeyHandling: false,
};

export const useStore = defineStore("settings", {
  state: () => ({ ...defaultState }),

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
    async saveSettings() {
      const messager = useMessagerStore();
      const popupStore = usePopupStore();
      if (popupStore.tab === SettingsTab.TTS) {
        return await this.saveTexts();
      }
      const data =
        popupStore.tab === SettingsTab.GENERAL
          ? omit(["keybindings"], this.settings)
          : { keybindings: this.settings.keybindings };
      this.saving = true;
      try {
        await axios.post("/api/settings", data);
        messager.success("Settings saved");
      } catch (error) {
        messager.handleError(error, "Error saving settings");
      } finally {
        this.saving = false;
      }
    },
    async saveTexts() {
      const messager = useMessagerStore();

      this.saving = true;
      try {
        await axios.post("/api/settings", {
          texts: this.settings.texts.filter((item) => !!item.text.length),
        });

        messager.success("Settings saved");
      } catch (error) {
        messager.handleError(error, "Error saving settings");
      } finally {
        this.saving = false;
      }
    },
    async saveAllSettings() {
      const messager = useMessagerStore();
      this.saving = true;
      try {
        await axios.post("/api/settings", this.settings);
        messager.success("Settings saved");
      } catch (error) {
        messager.handleError(error, "Error saving settings");
      } finally {
        this.saving = false;
      }
    },

    async saveData(data: Partial<Settings>) {
      const messager = useMessagerStore();
      this.saving = true;
      try {
        await axios.post("/api/settings", data);
        messager.success("Settings saved");
      } catch (error) {
        messager.handleError(error, "Error saving settings");
      } finally {
        this.saving = false;
      }
    },

    async fetchDimensions() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const { data } = await axios.get("api/frame-dimensions");
        const { height, width } = data;

        if (isNumber(height)) {
          this.dimensions.height = height;
        }
        if (isNumber(width)) {
          this.dimensions.width = width;
        }
      } catch (error) {
        messager.handleError(error, "Error fetching settings");
      } finally {
        this.loading = false;
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
