import axios from "axios";
import { defineStore } from "pinia";
import { useMessagerStore } from "@/features/messager";
import {
  downloadFile,
  removeFile,
  batchRemoveFiles,
} from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";
import { getBatchFilesErrorMessage } from "@/features/settings/util";

export interface FileItem {
  name: string;
  path: string;
  url: string;
}

export interface State {
  data: FileItem[];
  loading: boolean;
  emptyMessage?: string;
}

const defaultState: State = {
  loading: false,
  emptyMessage: "No photos",
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
        this.emptyMessage = defaultState["emptyMessage"];
        const response = await axios.get<{ files: FileItem[] }>(
          "/api/files/list/photos",
        );
        this.data = response.data.files;
      } catch (error) {
        messager.handleError(error, "Error fetching images");
        this.emptyMessage = "Failed to fetch photos";
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
    async batchRemoveFiles(filenames: string[]) {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const { data } = await batchRemoveFiles(mediaType, filenames);
        const msgParams = getBatchFilesErrorMessage(data);
        if (msgParams) {
          messager.error(msgParams.error, msgParams.title);
        }
      } catch (error) {
        messager.handleError(error);
      } finally {
        this.loading = false;
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
