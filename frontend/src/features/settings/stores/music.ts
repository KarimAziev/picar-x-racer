import axios from "axios";
import { defineStore } from "pinia";
import { constrain } from "@/util/constrain";
import { downloadFile, removeFile } from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";
import { useMessagerStore } from "@/features/messager/store";
import { isNumber } from "@/util/guards";

export interface State {
  data: string[];
  loading: boolean;
  defaultData: [];
  volume?: number;
}

const defaultState: State = {
  loading: false,
  data: [],
  defaultData: [],
};

export const mediaType: APIMediaType = "music";

export const useStore = defineStore("music", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get(`/api/list_files/${mediaType}`);
        this.data = response.data.files;
      } catch (error) {
        messager.handleError(error, `Error fetching ${mediaType}`);
      } finally {
        this.loading = false;
      }
    },

    async fetchDefaultData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get(`/api/list_files/default_music`);
        this.defaultData = response.data.files;
      } catch (error) {
        messager.handleError(error, `Error fetching ${mediaType}`);
      } finally {
        this.loading = false;
      }
    },

    async removeFile(file: string) {
      const messager = useMessagerStore();
      try {
        await removeFile(mediaType, file);
      } catch (error) {
        messager.handleError(error);
      }
    },
    async downloadFile(fileName: string) {
      const messager = useMessagerStore();
      try {
        await downloadFile(mediaType, fileName);
      } catch (error) {
        messager.handleError(error);
      }
    },

    async increaseVolume() {
      if (!isNumber(this.volume)) {
        await this.getVolume();
      }
      await this.setVolume(constrain(0, 100, (this.volume || 0) + 10));
    },

    async decreaseVolume() {
      if (!isNumber(this.volume)) {
        await this.getVolume();
      }
      await this.setVolume(constrain(0, 100, (this.volume || 100) - 10));
    },

    async setVolume(volume: number) {
      const messager = useMessagerStore();
      try {
        const response = await axios.post("/api/volume", { volume });
        this.volume = response.data.volume;
        messager.info(`Volume: ${this.volume}`);
      } catch (error) {
        messager.handleError(error);
      }
    },
    async getVolume() {
      const messager = useMessagerStore();
      try {
        const response = await axios.get<{ volume: number }>("/api/volume");
        this.volume = response.data.volume;
        messager.info(`Volume: ${this.volume}`);
        return this.volume;
      } catch (error) {
        messager.handleError(error);
      }
    },
  },
});
