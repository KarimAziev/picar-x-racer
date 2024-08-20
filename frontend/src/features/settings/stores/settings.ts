import { defineStore } from "pinia";
import axios from "axios";
import { handleError } from "@/util/error";
import { defaultKeybindinds } from "@/features/settings/defaultKeybindings";

export interface State {
  open?: boolean;
  loading?: boolean;
  settings: {
    default_text: string;
    default_sound: string;
    default_music: string;
    keybindings: Record<string, string[]>;
  };
}

const defaultState: State = {
  open: false,
  settings: {
    keybindings: {},
    default_text: "",
    default_sound: "",
    default_music: "",
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
      } catch (error) {
        handleError(error, "Error saving settings");
      } finally {
        this.loading = false;
      }
    },
  },
});
