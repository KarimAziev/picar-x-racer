import axios from "axios";
import { defineStore } from "pinia";
import { useMessagerStore } from "@/features/messager";
import { downloadFile, removeFile } from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";

export interface FileItem {
  name: string;
  path: string;
  url: string;
}

export interface State {
  data: FileItem[];
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
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get<{ files: FileItem[] }>(
          "/api/files/list/photos",
        );
        this.data = response.data.files;
      } catch (error) {
        messager.handleError(error, "Error fetching images");
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
