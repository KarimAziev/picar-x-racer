import axios from "axios";
import { defineStore } from "pinia";
import { downloadFile, removeFile } from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";
import { handleError } from "@/util/error";

export interface State {
  data: string[];
  loading: boolean;
}

const defaultState: State = {
  loading: false,
  data: [],
};

export const mediaType: APIMediaType = "music";

export const useStore = defineStore("music", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      try {
        this.loading = true;
        const response = await axios.get(`/api/list_files/${mediaType}`);
        this.data = response.data.files;
      } catch (error) {
        handleError(error, `Error fetching ${mediaType}`);
      } finally {
        this.loading = false;
      }
    },

    async removeFile(file: string) {
      return await removeFile(mediaType, file);
    },
    async downloadFile(fileName: string) {
      return await downloadFile(mediaType, fileName);
    },
  },
});