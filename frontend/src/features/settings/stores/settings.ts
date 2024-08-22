import { defineStore } from "pinia";
import axios from "axios";
import { handleError } from "@/util/error";
import { defaultKeybindinds } from "@/features/settings/defaultKeybindings";
import { messager } from "@/util/message";
import { VideoFeedURL } from "@/features/settings/enums";

export interface State {
  loading?: boolean;
  settings: {
    fullscreen: boolean;
    default_text: string;
    default_sound: string;
    default_music: string;
    keybindings: Record<string, string[]>;
    video_feed_url: VideoFeedURL;
    battery_full_voltage: number;
  };
}

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
};

export const useStore = defineStore("settings", {
  state: () => ({ ...defaultState }),

  actions: {
    async fetchSettings() {
      try {
        this.loading = true;
        const response = await axios.get("/api/settings");
        const data = {
          ...this.settings,
          keybindings: { ...defaultKeybindinds },
          ...response.data,
        };
        this.settings = data;
      } catch (error) {
        console.error("Error fetching settings:", error);
        handleError(error, "Error fetching settings");
      } finally {
        this.loading = false;
      }
    },
    async saveSettings() {
      this.loading = true;
      try {
        await axios.post("/api/settings", this.settings);
        messager.success("Settings saved");
      } catch (error) {
        handleError(error, "Error saving settings");
      } finally {
        this.loading = false;
      }
    },
    increaseQuality() {
      const levels = [VideoFeedURL.lq, VideoFeedURL.mq, VideoFeedURL.hq];
      const idx = levels.indexOf(this.settings.video_feed_url);
      const nextURL = levels[idx + 1];
      if (nextURL) {
        this.settings.video_feed_url = nextURL;
        messager.info(`Increased quality to ${nextURL.split("-").pop()}`);
      } else {
        messager.info(`${this.settings.video_feed_url} is highest quality `);
      }
    },
    decreaseQuality() {
      const levels = [VideoFeedURL.lq, VideoFeedURL.mq, VideoFeedURL.hq];
      const idx = levels.indexOf(this.settings.video_feed_url);
      const nextURL = levels[idx - 1];
      if (nextURL) {
        this.settings.video_feed_url = nextURL;
        messager.info(`Decreased quality to ${nextURL.split("-").pop()}`);
      } else {
        messager.info(`${this.settings.video_feed_url} is lowest quality!`);
      }
    },
  },
});
