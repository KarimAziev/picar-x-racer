import { defineStore } from "pinia";
import axios from "axios";
import { defaultKeybindinds } from "@/features/settings/defaultKeybindings";
import { VideoFeedURL } from "@/features/settings/enums";
import { useMessagerStore } from "@/features/messager/store";
import { wait } from "@/util/wait";
import { isNumber } from "@/util/guards";

export interface Settings {
  fullscreen: boolean;
  default_text: string;
  default_sound: string;
  default_music: string;
  keybindings: Record<string, string[]>;
  video_feed_url: VideoFeedURL;
  battery_full_voltage: number;
  text_info_view?: boolean;
  speedometer_view?: boolean;
  car_model_view?: boolean;
}

export interface State {
  loading?: boolean;
  loaded?: boolean;
  saving?: boolean;
  settings: Settings;
  dimensions: { width: number; height: number };
}

export type ToggleableSettings = {
  [K in keyof Settings as Required<Settings>[K] extends boolean
    ? K
    : never]: Settings[K];
};

const defaultState: State = {
  settings: {
    fullscreen: true,
    keybindings: {},
    default_text: "",
    default_sound: "",
    default_music: "",
    video_feed_url: VideoFeedURL.lq,
    battery_full_voltage: 8.4,
  },
  dimensions: { width: 1280, height: 720 },
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
        this.fetchDimensions();
      } catch (error) {
        messager.handleError(error, "Error fetching settings");
      } finally {
        this.loading = false;
      }
    },
    async fetchSettingsInitial() {
      const messager = useMessagerStore();
      messager.info("loading...");
      try {
        this.loading = true;
        await wait(1000);
        await this.fetchSettings();
        await wait(500);
        messager.info("Memory set: OK_");
        await wait(500);
        messager.info("System status: OK_");
        await wait(500);
      } catch (error) {
        console.error("Error fetching settings:", error);
        messager.handleError(error, "Error fetching settings");
      } finally {
        this.loading = false;
        this.loaded = true;
      }
    },
    async saveSettings() {
      const messager = useMessagerStore();
      this.saving = true;
      try {
        await wait(2000);
        await axios.post("/api/settings", this.settings);
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
    async increaseQuality() {
      const messager = useMessagerStore();
      const levels = [VideoFeedURL.lq, VideoFeedURL.mq, VideoFeedURL.hq];
      const idx = levels.indexOf(this.settings.video_feed_url);
      const nextURL = levels[idx + 1];
      if (nextURL) {
        await wait(1000);
        this.settings.video_feed_url = nextURL;
        await this.fetchDimensions();
        messager.info(`Increased quality to ${nextURL.split("-").pop()}`);
      } else {
        messager.info(`${this.settings.video_feed_url} is highest quality `);
      }
    },
    async decreaseQuality() {
      const messager = useMessagerStore();
      const levels = [VideoFeedURL.lq, VideoFeedURL.mq, VideoFeedURL.hq];
      const idx = levels.indexOf(this.settings.video_feed_url);
      const nextURL = levels[idx - 1];
      if (nextURL) {
        await wait(1000);
        this.settings.video_feed_url = nextURL;
        await this.fetchDimensions();
        messager.info(`Decreased quality to ${nextURL.split("-").pop()}`);
      } else {
        messager.info(`${this.settings.video_feed_url} is lowest quality!`);
      }
    },
    toggleSettingsProp(prop: keyof ToggleableSettings) {
      const messager = useMessagerStore();
      if (this.settings[prop]) {
        this.settings[prop] = false;
      } else {
        this.settings[prop] = true;
      }
      messager.info(`${prop} setted to ${this.settings[prop]}`);
    },
  },
});
