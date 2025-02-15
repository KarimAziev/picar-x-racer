import axios from "axios";
import { defineStore } from "pinia";
import { useMessagerStore } from "@/features/messager";
import {
  downloadFile,
  removeFile,
  batchRemoveFiles,
  downloadFilesAsArchive,
} from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";
import { getBatchFilesErrorMessage } from "@/features/settings/util";
import { Nullable } from "@/util/ts-helpers";

export interface FileItem {
  track: string;
  duration: number;
  preview?: Nullable<string>;
}

export interface State {
  data: FileItem[];
  loading: boolean;
  emptyMessage?: string;
}

const defaultState: State = {
  loading: false,
  emptyMessage: "No videos",
  data: [],
};

export const mediaType: APIMediaType = "video";
export const useStore = defineStore("videos", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        this.emptyMessage = defaultState["emptyMessage"];
        const response = await axios.get<FileItem[]>("/api/files/list/videos");
        this.data = response.data;
      } catch (error) {
        messager.handleError(error, "Error fetching videos");
        this.emptyMessage = "Failed to fetch videos";
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
      const progressFn = messager.makeProgress("Downloading");
      try {
        await downloadFile(mediaType, fileName, progressFn);
      } catch (error) {
        messager.handleError(error);
      }
    },
    async downloadFilesArchive(filenames: string[]) {
      const messager = useMessagerStore();

      const progressFn = messager.makeProgress("Downloading video archive");
      try {
        await downloadFilesAsArchive(mediaType, filenames, progressFn);
      } catch (error) {
        messager.handleError(error);
      }
    },
  },
});
