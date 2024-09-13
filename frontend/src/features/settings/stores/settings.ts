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

export type ToggleableSettings = {
  [P in keyof typeof toggleableSettings]: boolean;
};

export interface CameraOpenRequestParams {
  video_feed_fps?: number;
  video_feed_format?: string;
  video_feed_enhance_mode: string | null;
  video_feed_detect_mode: string | null;
  video_feed_quality?: number;
  video_feed_height?: number;
  video_feed_width?: number;
}

export interface Settings extends Partial<ToggleableSettings> {
  default_text: string;
  default_sound: string;
  default_language: string;
  default_music: string;
  keybindings: Partial<Record<ControllerActionName, string[]>>;
  battery_full_voltage: number;
  auto_measure_distance_delay_ms: number;
  video_feed_quality: number;
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
}

const defaultState: State = {
  settings: {
    fullscreen: true,
    keybindings: {},
    default_text: "",
    default_sound: "",
    default_language: "en",
    default_music: "",
    battery_full_voltage: 8.4,
    auto_measure_distance_delay_ms: 1000,
    video_feed_quality: 100,
  },
  dimensions: { width: 640, height: 480 },
  retryCounter: 0,
};

export const useStore = defineStore("settings", {
  state: () => ({ ...defaultState }),

  actions: {
    async fetchSettings() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get("/api/settings");

        const data = {
          ...this.settings,
          keybindings: { ...defaultKeybindinds },
          ...response.data,
        };
        this.settings = data;
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
          musicStore.fetchDefaultData(),
          musicStore.fetchData(),
          musicStore.getCurrentStatus(),
          soundStore.fetchDefaultData(),
          soundStore.fetchData(),
        ]);
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
    nextFrameEnhancerMode(
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
    prevFrameEnhancerMode(
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
  },
});
