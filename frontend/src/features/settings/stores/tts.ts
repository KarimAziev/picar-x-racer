import { defineStore } from "pinia";
import { useMessagerStore } from "@/features/messager";
import { appApi } from "@/api";

export interface LanguageOption {
  value: string;
  label: string;
}

export interface State {
  data: LanguageOption[];
  loading?: boolean;
}

export const useStore = defineStore("tts", {
  state: (): State => ({ data: [] }),
  actions: {
    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const data = await appApi.get<LanguageOption[]>("/api/tts/languages");
        this.data = data;
      } catch (error) {
        messager.handleError(error);
      } finally {
        this.loading = false;
      }
    },
    async fetchLanguagesOnce() {
      if (!this.data.length) {
        await this.fetchData();
      }
    },
  },
});
