import { defineStore } from "pinia";
import axios from "axios";
import type { TreeNode } from "primevue/treenode";
import { useMessagerStore } from "@/features/messager/store";
import { constrain } from "@/util/constrain";
import { cycleValue } from "@/util/cycleValue";
import {
  CameraOpenRequestParams,
  useStore as useSettingsStore,
} from "@/features/settings/stores/settings";

export const dimensions = [
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

export interface DeviceSuboption extends TreeNode {
  device: string;
  size: string;
  fps: string;
  pixel_format: string;
}

export interface DeviceOption extends Pick<DeviceSuboption, "key" | "label"> {
  children: DeviceSuboption[];
}

export type LoadingFields = Partial<{
  [P in keyof CameraOpenRequestParams]: boolean;
}>;

export interface State {
  data: CameraOpenRequestParams;
  loading: boolean;
  detectors: TreeNode[];
  enhancers: string[];
  devices: DeviceOption[];
  loadingData: LoadingFields;
}

const defaultState: State = {
  loading: false,
  data: {
    video_feed_enhance_mode: null,
    video_feed_detect_mode: null,
    video_feed_height: 600,
    video_feed_width: 800,
    video_feed_device: null,
    video_feed_pixel_format: null,
    video_feed_object_detection: false,
  },
  detectors: [],
  enhancers: [],
  devices: [],
  loadingData: {},
};

export const useStore = defineStore("camera", {
  state: () => ({ ...defaultState }),
  actions: {
    async updateCameraParams(payload?: Partial<CameraOpenRequestParams>) {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        const requestData = payload || this.data;
        this.loadingData = {};
        Object.keys(requestData).forEach((key) => {
          this.loadingData[key as keyof CameraOpenRequestParams] = true;
        });

        const prevData = { ...this.data };

        const { data } = await axios.post<CameraOpenRequestParams>(
          "/api/video-feed-settings",
          payload || this.data,
        );
        this.data = data;
        Object.entries(data).forEach(([k, value]) => {
          const key = k as keyof CameraOpenRequestParams;
          this.loadingData[key] = false;
          if (prevData[key] !== value) {
            messager.info(`${key.replace(/^video_feed_/g, "")}: ${value}`, {
              immediately: true,
            });
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
        this.loadingData = {};
      }
      return this.data;
    },

    async fetchAllCameraSettings() {
      await Promise.all([this.fetchCurrentSettings(), this.fetchDevices()]);
    },

    async fetchCurrentSettings() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const { data } = await axios.get<CameraOpenRequestParams>(
          "/api/video-feed-settings",
        );
        this.data = data;
      } catch (error) {
        messager.handleError(error, "Error fetching video feed settings");
      } finally {
        this.loading = false;
      }
    },

    async fetchDevices() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const { data } = await axios.get<{ devices: DeviceOption[] }>(
          "/api/camera-devices",
        );
        this.devices = data.devices;
      } catch (error) {
        messager.handleError(error, "Error fetching camera devices");
      } finally {
        this.loading = false;
      }
    },

    async fetchConfig() {
      await Promise.all([this.fetchModels(), this.fetchEnhancers()]);
    },

    async fetchEnhancers() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get("/api/enhancers");
        const data = response.data;
        this.enhancers = data.enhancers;
      } catch (error) {
        messager.handleError(error, "Error fetching video enhancers");
      } finally {
        this.loading = false;
      }
    },

    async fetchModels() {
      const messager = useMessagerStore();
      this.loading = true;
      try {
        const response = await axios.get<TreeNode[]>("/api/detection-models");
        this.detectors = response.data;
      } catch (error) {
        messager.handleError(error, "Error fetching detection models");
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
    async toggleDetection() {
      await this.updateCameraParams({
        video_feed_object_detection: !this.data.video_feed_object_detection,
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
    async toggleRecording() {
      const settings = useSettingsStore();
      const messager = useMessagerStore();
      await this.updateCameraParams({
        video_feed_record: !this.data.video_feed_record,
      });

      if (
        !this.data.video_feed_record &&
        settings.settings.auto_download_video
      ) {
        try {
          const response = await axios.get(`/api/download-last-video`, {
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
