import { defineStore } from "pinia";
import axios from "axios";

export interface State {
  loading: boolean;
  settings: {
    default_text: string;
    default_sound: string;
    default_music: string;
  };
  sounds: string[];
  music: string[];
  images: string[];
  uploadProgress: number;
}

const defaultState: State = {
  loading: false,
  settings: {
    default_text: "",
    default_sound: "",
    default_music: "",
  },
  sounds: [],
  music: [],
  images: [],
  uploadProgress: 0,
};

export const useSettingsStore = defineStore("settings", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchSettings() {
      this.loading = true;
      try {
        const response = await axios.get("/api/settings");
        this.settings = response.data;
      } catch (error) {
        console.error("Error fetching settings:", error);
      } finally {
        this.loading = false;
      }
    },
    async saveSettings() {
      this.loading = true;
      try {
        await axios.post("/api/settings", this.settings);
      } catch (error) {
        console.error("Error saving settings:", error);
      } finally {
        this.loading = false;
      }
    },
    async fetchSounds() {
      try {
        const response = await axios.get("/api/list_files/sound");
        this.sounds = response.data.files;
      } catch (error) {
        console.error("Error fetching sounds:", error);
      }
    },
    async fetchMusic() {
      try {
        const response = await axios.get("/api/list_files/music");
        this.music = response.data.files;
      } catch (error) {
        console.error("Error fetching music:", error);
      }
    },
    async fetchImages() {
      try {
        const response = await axios.get("/api/list_files/image");
        this.images = response.data.files;
      } catch (error) {
        console.error("Error fetching images:", error);
      }
    },

    async removeImageFile(file: string) {
      try {
        await axios.delete(`/api/remove_file/image`, {
          data: { filename: file },
        });
      } catch (error) {
        console.error(`Error removing ${file}`, error);
      }
    },
    async removeSoundFile(file: string) {
      try {
        await axios.delete(`/api/remove_file/sound`, {
          data: { filename: file },
        });
        await this.fetchSounds();
      } catch (error) {
        console.error(`Error removing ${file}`, error);
      }
    },
    async removeMusicFile(file: string) {
      try {
        await axios.delete(`/api/remove_file/music`, {
          data: { filename: file },
        });
        await this.fetchMusic();
      } catch (error) {
        console.error(`Error removing ${file}`, error);
      }
    },
    async downloadFile(mediaType: string, fileName: string) {
      try {
        const response = await axios.get(
          `/api/download/${mediaType}/${fileName}`,
          {
            responseType: "blob",
          },
        );
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement("a");

        link.href = url;
        link.setAttribute("download", fileName);
        document.body.appendChild(link);
        link.click();
      } catch (error) {
        console.error(`Error downloading ${mediaType} file:`, error);
      }
    },
  },
});
