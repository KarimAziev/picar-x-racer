import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager/store";
import { constrain } from "@/util/constrain";
import { wait } from "@/util/wait";
import { cycleValue } from "@/util/cycleValue";
import {
  CameraOpenRequestParams,
  useStore as useSettingsStore,
} from "@/features/settings/stores/settings";

const dimensions = [
  [640, 480],
  [800, 600],
  [1024, 768],
  [1280, 720],
  [1280, 800],
  [1366, 768],
  [1440, 900],
  [1600, 900],
  [1680, 1050],
  [1920, 1080],
  [1920, 1200],
];

const MAX_FPS = 70;

export interface State {
  data: CameraOpenRequestParams;
  dimensions: { video_feed_width: number; video_feed_height: number } | null;
  loading: boolean;
  cancelTokenSource?: AbortController;
  detectors: string[];
  enhancers: string[];
}

const defaultState: State = {
  loading: false,
  data: {
    video_feed_enhance_mode: null,
    video_feed_detect_mode: null,
  },
  detectors: [],
  enhancers: [],
  dimensions: null,
  cancelTokenSource: undefined,
};

export const useStore = defineStore("camera", {
  state: () => ({ ...defaultState }),
  actions: {
    async updateCameraParams(payload?: Partial<CameraOpenRequestParams>) {
      const messager = useMessagerStore();

      if (this.cancelTokenSource) {
        this.cancelTokenSource.abort();
      }

      const cancelTokenSource = new AbortController();
      this.cancelTokenSource = cancelTokenSource;

      try {
        this.loading = true;
        const { data } = await axios.post<CameraOpenRequestParams>(
          "/api/video-feed-settings",
          payload || this.data,
          { signal: cancelTokenSource.signal },
        );
        await wait(500);
        this.data = data;
        Object.entries(data).forEach(([key, value]) => {
          if (payload && key in payload) {
            messager.info(`${key}: ${value}`, { immediately: true });
          }
        });
      } catch (error) {
        if (axios.isCancel(error)) {
          console.log("Request canceled:", error.message);
        } else {
          messager.handleError(error, `Error starting camera`);
        }
      } finally {
        this.loading = false;
        this.cancelTokenSource = undefined;
      }
      return this.data;
    },

    async fetchCurrentSettings() {
      try {
        this.loading = true;
        const { data } = await axios.get<CameraOpenRequestParams>(
          "/api/video-feed-settings",
        );
        this.data = data;
      } catch (error) {
        console.error("Error fetching video modes:", error);
      } finally {
        this.loading = false;
      }
    },

    async fetchConfig() {
      try {
        this.loading = true;
        const response = await axios.get("/api/video-modes");
        const data = response.data;
        this.detectors = data.detectors;
        this.enhancers = data.enhancers;
      } catch (error) {
        console.error("Error fetching video modes:", error);
      } finally {
        this.loading = false;
      }
    },

    async ensureConfig() {
      if (!this.loading && !this.detectors.length && !this.enhancers.length) {
        await this.fetchConfig();
      }
    },
    async increaseFPS() {
      const video_feed_fps = this.data.video_feed_fps || 30;
      await this.updateCameraParams({
        video_feed_fps: constrain(10, MAX_FPS, video_feed_fps + 10),
      });
    },
    async decreaseFPS() {
      const video_feed_fps = this.data.video_feed_fps || 30;
      await this.updateCameraParams({
        video_feed_fps: constrain(5, MAX_FPS, Math.max(5, video_feed_fps - 10)),
      });
    },
    async nextDetectMode() {
      await this.ensureConfig();
      const currentMode = this.data.video_feed_detect_mode;
      this.data.video_feed_detect_mode = cycleValue(
        currentMode,
        [...this.detectors, null],
        1,
      );

      await this.updateCameraParams({
        video_feed_detect_mode: this.data.video_feed_detect_mode,
      });
    },
    async nextEnhanceMode() {
      await this.ensureConfig();
      const currentMode = this.data.video_feed_enhance_mode;
      const nextMode = cycleValue(currentMode, [...this.enhancers, null], 1);

      await this.updateCameraParams({
        video_feed_enhance_mode: nextMode,
      });
    },
    async prevDetectMode() {
      await this.ensureConfig();
      const currentMode = this.data.video_feed_detect_mode;
      this.data.video_feed_detect_mode = cycleValue(
        currentMode,
        [...this.detectors, null],
        -1,
      );

      await this.updateCameraParams({
        video_feed_detect_mode: this.data.video_feed_detect_mode,
      });
    },
    async prevEnhanceMode() {
      await this.ensureConfig();
      const currentMode = this.data.video_feed_enhance_mode;
      this.data.video_feed_enhance_mode = cycleValue(
        currentMode,
        [...this.enhancers, null],
        -1,
      );

      await this.updateCameraParams({
        video_feed_enhance_mode: this.data.video_feed_enhance_mode,
      });
    },
    async increaseQuality() {
      const settings = useSettingsStore();
      const currentValue =
        this.data.video_feed_quality || settings.settings.video_feed_quality;
      const newValue = constrain(10, 100, currentValue + 10);
      await this.updateCameraParams({
        video_feed_quality: newValue,
      });
    },
    async decreaseQuality() {
      const settings = useSettingsStore();
      const currentValue =
        this.data.video_feed_quality || settings.settings.video_feed_quality;
      const newValue = constrain(10, 100, currentValue - 10);
      await this.updateCameraParams({
        video_feed_quality: newValue,
      });
    },
    async increaseDimension() {
      const currHeight = this.data?.video_feed_height;
      const currWidth = this.data?.video_feed_width;

      const idx =
        dimensions.findIndex(
          ([video_feed_width, video_feed_height]) =>
            video_feed_width === currWidth && video_feed_height === currHeight,
        ) || 0;
      const [video_feed_width, video_feed_height] =
        dimensions[idx + 1] || dimensions[0];
      await this.updateCameraParams({
        video_feed_height,
        video_feed_width,
      });
    },
    async decreaseDimension() {
      const currHeight = this.data?.video_feed_height;
      const currWidth = this.data?.video_feed_width;

      const idx =
        dimensions.findIndex(
          ([video_feed_width, video_feed_height]) =>
            video_feed_width === currWidth && video_feed_height === currHeight,
        ) || 0;
      const [video_feed_width, video_feed_height] =
        dimensions[idx - 1] || dimensions[dimensions.length - 1];
      await this.updateCameraParams({
        video_feed_height,
        video_feed_width,
      });
    },
  },
});
