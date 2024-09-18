import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager/store";
import { downloadFile, removeFile } from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";

export interface State {
  data: string[];
  defaultData: [];
  loading: boolean;
}

const defaultState: State = {
  loading: false,
  data: [],
  defaultData: [],
};

export const mediaType: APIMediaType = "sound";

export const useStore = defineStore("sounds", {
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
        const response = await axios.get(`/api/list_files/default_sound`);
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
    async playSound(name: string) {
      const messager = useMessagerStore();
      try {
        const response = await axios.post(`/api/play-sound`, {
          filename: name,
        });
        const data = response.data;
        const msg = data.playing ? `Playing ${name}` : "Stoped playing";
        messager.info(msg);
      } catch (error) {
        messager.handleError(error);
      }
    },
    async handleFileUpload(fileBlob: Blob) {
      const messager = useMessagerStore();
      const formData = new FormData();
      formData.append("file", fileBlob);

      try {
        const response = await axios.post<{
          filename: string;
          success: boolean;
        }>(`/api/upload/${mediaType}`, formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
        return response.data;
      } catch (error) {
        messager.handleError(error);
      }
    },
  },
});
