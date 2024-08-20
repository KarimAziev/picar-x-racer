import { defineStore } from "pinia";
import axios from "axios";
import { handleError } from "@/util/error";
import { downloadFile, removeFile } from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";

export interface State {
  data: string[];
  loading: boolean;
}

const defaultState: State = {
  loading: false,
  data: [],
};
export const mediaType: APIMediaType = "image";
export const useStore = defineStore("images", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      const mediaType: APIMediaType = "image";
      try {
        this.loading = true;
        const response = await axios.get(`/api/list_files/${mediaType}`);
        this.data = response.data.files;
      } catch (error) {
        handleError(error, "Error fetching images");
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
