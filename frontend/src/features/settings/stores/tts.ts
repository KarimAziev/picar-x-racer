import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager/store";

export interface TTSConfigResponse {
  languages: Language[];
}

interface TTSResponse {
  texts: TextItem[];
}

export interface TextItem {
  text: string;
  language: string;
  default?: boolean;
}

export interface Language {
  label: string;
  value: string;
}

export interface State {
  data: TextItem[];
  languages: Language[];
  saving?: boolean;
  loading?: boolean;
}

const defaultState: State = {
  loading: false,
  languages: [],
  data: [],
};

export const useStore = defineStore("tts", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchConfig() {
      const messager = useMessagerStore();
      try {
        const response = await axios.get<TTSConfigResponse>(`/api/tts-config`);
        this.languages = response.data.languages;
      } catch (error) {
        messager.handleError(error, `Error fetching TextItem Speech config`);
      }
    },
    async fetchTexts() {
      const messager = useMessagerStore();
      try {
        const response = await axios.get<TTSResponse>(`/api/tts-settings`);
        this.data = response.data.texts;
      } catch (error) {
        messager.handleError(error, `Error fetching texts`);
      }
    },
    async saveTexts() {
      const messager = useMessagerStore();

      try {
        this.saving = true;
        const response = await axios.post<TTSResponse>(
          `/api/tts-settings`,
          this.data.filter((item) => !!item.text.length),
        );
        const mergedData = this.data.filter((item) => item.text.length);
        this.data = response.data.texts.concat(mergedData);
      } catch (error) {
        messager.handleError(error, `Error fetching texts`);
      } finally {
        this.saving = false;
      }
    },
    async fetchAll() {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        await this.fetchConfig();
        await this.fetchTexts();
      } catch (error) {
        messager.handleError(error, `Error fetching texts`);
      } finally {
        this.loading = false;
      }
    },
  },
});
