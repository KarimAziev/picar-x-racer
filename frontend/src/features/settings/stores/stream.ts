import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager/store";
import { constrain } from "@/util/constrain";
import { cycleValue } from "@/util/cycleValue";
import {
  StreamSettings,
  useStore as useSettingsStore,
  defaultState as settingsDefaultState,
} from "@/features/settings/stores/settings";

export interface State {
  data: StreamSettings;
  loading: boolean;
  enhancers: string[];
}

const defaultState: State = {
  loading: false,
  data: { ...settingsDefaultState.data.stream },
  enhancers: [],
};

export const useStore = defineStore("stream", {
  state: () => ({ ...defaultState }),
  actions: {
    async updateData(payload?: StreamSettings) {
      const messager = useMessagerStore();

      try {
        this.loading = true;

        await axios.post<StreamSettings>(
          "/api/video-feed/settings",
          payload || this.data,
        );
      } catch (error) {
        if (axios.isCancel(error)) {
          console.log("Request canceled:", error.message);
        } else {
          messager.handleError(error, `Error starting camera`);
        }
      } finally {
        this.loading = false;
      }
      return this.data;
    },

    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const { data } = await axios.get<StreamSettings>(
          "/api/video-feed/settings",
        );
        this.data = data;
      } catch (error) {
        messager.handleError(error, "Error fetching video feed settings");
      } finally {
        this.loading = false;
      }
    },
    async fetchEnhancers() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get("/api/video-feed/enhancers");
        const data = response.data;
        this.enhancers = data.enhancers;
      } catch (error) {
        messager.handleError(error, "Error fetching video enhancers");
      } finally {
        this.loading = false;
      }
    },
    async nextEnhanceMode() {
      const currentMode = this.data.enhance_mode;
      const nextMode = cycleValue(currentMode, [...this.enhancers, null], 1);

      await this.updateData({
        ...this.data,
        enhance_mode: nextMode,
      });
    },
    async prevEnhanceMode() {
      const currentMode = this.data.enhance_mode;
      this.data.enhance_mode = cycleValue(
        currentMode,
        [...this.enhancers, null],
        -1,
      );

      await this.updateData({
        ...this.data,
        enhance_mode: this.data.enhance_mode,
      });
    },
    async increaseQuality() {
      const settings = useSettingsStore();
      const currentValue = this.data.quality || settings.data.stream.quality;
      const newValue = constrain(10, 100, currentValue + 10);
      await this.updateData({
        ...this.data,
        quality: newValue,
      });
    },
    async decreaseQuality() {
      const settings = useSettingsStore();
      const currentValue = this.data.quality || settings.data.stream.quality;
      const newValue = constrain(10, 100, currentValue - 10);
      await this.updateData({
        ...this.data,
        quality: newValue,
      });
    },
    async toggleRecording() {
      const settings = useSettingsStore();
      const messager = useMessagerStore();
      await this.updateData({
        ...this.data,
        video_record: !this.data.video_record,
      });

      if (!this.data.video_record && settings.data.auto_download_video) {
        try {
          const response = await axios.get(`/api/files/download-last-video`, {
            responseType: "blob",
          });
          const fileName = response.headers["content-disposition"]
            ? response.headers["content-disposition"].split("filename=")[1]
            : "picar-x-recording.avi";
          const url = window.URL.createObjectURL(new Blob([response.data]));
          const link = document.createElement("a");

          link.href = url;
          link.setAttribute("download", fileName);
          document.body.appendChild(link);
          link.click();
        } catch (error) {
          messager.handleError(error);
        }
      }
    },
  },
});
