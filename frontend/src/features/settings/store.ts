import { defineStore } from "pinia";
import axios from "axios";
import { handleError } from "@/util/error";

export interface State {
  loading: boolean;
  settingsLoading: boolean;
  soundsLoading: boolean;
  musicLoading: boolean;
  imagesLoading: boolean;
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
  settingsLoading: false,
  soundsLoading: false,
  musicLoading: false,
  imagesLoading: false,
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
      try {
        this.settingsLoading = true;
        const response = await axios.get("/api/settings");
        this.settings = response.data;
      } catch (error) {
        console.error("Error fetching settings:", error);
        handleError(error, "Error fetching settings");
      } finally {
        this.settingsLoading = false;
      }
    },
    async saveSettings() {
      this.settingsLoading = true;
      try {
        await axios.post("/api/settings", this.settings);
      } catch (error) {
        handleError(error, "Error saving settings");
      } finally {
        this.settingsLoading = false;
      }
    },
    async fetchSounds() {
      try {
        this.soundsLoading = true;
        const response = await axios.get("/api/list_files/sound");
        this.sounds = response.data.files;
      } catch (error) {
        handleError(error, "Error fetching sounds");
      } finally {
        this.soundsLoading = false;
      }
    },
    async fetchMusic() {
      try {
        this.musicLoading = true;
        const response = await axios.get("/api/list_files/music");
        this.music = response.data.files;
      } catch (error) {
        handleError(error, "Error fetching music");
      } finally {
        this.musicLoading = false;
      }
    },
    async fetchImages() {
      try {
        this.imagesLoading = true;
        const response = await axios.get("/api/list_files/image");
        this.images = response.data.files;
      } catch (error) {
        handleError(error, "Error fetching images");
      } finally {
        this.imagesLoading = false;
      }
    },

    async fetchAll() {
      const promises = [
        this.fetchSettings,
        this.fetchImages,
        this.fetchSounds,
        this.fetchMusic,
      ];
      try {
        this.loading = true;
        await Promise.all(promises);
      } catch (error) {
        handleError(error, "Error fetching data");
      } finally {
        this.loading = false;
      }
    },

    async removeImageFile(file: string) {
      try {
        await axios.delete(`/api/remove_file/image`, {
          data: { filename: file },
        });
      } catch (error) {
        handleError(error, `Error removing ${file}`);
      }
    },
    async removeSoundFile(file: string) {
      try {
        await axios.delete(`/api/remove_file/sound`, {
          data: { filename: file },
        });
        await this.fetchSounds();
      } catch (error) {
        handleError(error, `Error removing ${file}`);
      }
    },
    async removeMusicFile(file: string) {
      try {
        await axios.delete(`/api/remove_file/music`, {
          data: { filename: file },
        });
        await this.fetchMusic();
      } catch (error) {
        handleError(error, `Error removing ${file}`);
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
        handleError(error, `Error downloading ${mediaType} file`);
      }
    },
  },
});
