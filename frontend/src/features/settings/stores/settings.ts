import { defineStore } from "pinia";
import axios from "axios";
import { defaultKeybindinds } from "@/features/settings/defaultKeybindings";
import { VideoFeedURL } from "@/features/settings/enums";
import { useMessagerStore } from "@/features/messager/store";

export const wait = async (delay: number) =>
  new Promise((resolve) => setTimeout(resolve, delay));

export interface State {
  loading?: boolean;
  loaded?: boolean;
  saving?: boolean;
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
      const messager = useMessagerStore();
      try {
        if (!this.loaded) {
          messager.info("Loading...");
        }

        this.loading = true;
        await wait(1000);
        const response = await axios.get("/api/settings");

        const data = {
          ...this.settings,
          keybindings: { ...defaultKeybindinds },
          ...response.data,
        };
        this.settings = data;
        if (!this.loaded) {
          messager.info("Memory loaded: OK");
        }
      } catch (error) {
        console.error("Error fetching settings:", error);
        messager.handleError(error, "Error fetching settings");
      } finally {
        this.loading = false;
        // this.loaded = true;
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
    increaseQuality() {
      const messager = useMessagerStore();
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
      const messager = useMessagerStore();
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
