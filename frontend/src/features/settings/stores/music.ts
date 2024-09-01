import axios from "axios";
import { defineStore } from "pinia";
import { downloadFile, removeFile } from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";
import { useMessagerStore } from "@/features/messager/store";

export interface State {
  data: string[];
  loading: boolean;
  defaultData: [];
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
  },
});
