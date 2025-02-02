import axios from "axios";
import { defineStore } from "pinia";

import { useMessagerStore } from "@/features/messager";
import { constrain } from "@/util/constrain";
import {
  DeviceNode,
  Device,
  CameraSettings,
} from "@/features/settings/interface";
import { retrieveError } from "@/util/error";
import { groupDevices } from "@/features/settings/util";

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

export interface PhotoCaptureResponse {
  file: string;
}

export interface State {
  data: CameraSettings;
  loading: boolean;
  devices: DeviceNode[];
  error: string | null;
}

export const defaultState: State = {
  loading: false,
  data: {},
  devices: [],
  error: null,
};

export const useStore = defineStore("camera", {
  state: () => ({ ...defaultState }),
  actions: {
    async updateData(payload: CameraSettings) {
      const messager = useMessagerStore();

      try {
        this.loading = true;

        await axios.post<CameraSettings>(
          "/api/camera/settings",
          payload || this.data,
        );
      } catch (error) {
        if (axios.isCancel(error)) {
          console.log("Request canceled:", error.message);
        } else {
          this.error = retrieveError(error).text;
          messager.handleError(error);
        }
      } finally {
        this.loading = false;
      }
      return this.data;
    },

    async fetchAllCameraSettings() {
      await Promise.all([this.fetchDevices(), this.fetchData()]);
    },

    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const { data } = await axios.get<CameraSettings>(
          "/api/camera/settings",
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
        const { data } = await axios.get<{ devices: Device[] }>(
          "/api/camera/devices",
        );
        this.devices = groupDevices(data.devices);
      } catch (error) {
        messager.handleError(error, "Error fetching camera devices");
      } finally {
        this.loading = false;
      }
    },

    async increaseFPS() {
      const video_feed_fps = this.data.fps || 30;
      await this.updateData({
        ...this.data,
        fps: constrain(10, MAX_FPS, video_feed_fps + 10),
      });
    },
    async decreaseFPS() {
      const video_feed_fps = this.data.fps || 30;
      await this.updateData({
        ...this.data,
        fps: constrain(5, MAX_FPS, Math.max(5, video_feed_fps - 10)),
      });
    },

    async increaseDimension() {
      const currHeight = this.data?.height;
      const currWidth = this.data?.width;

      const idx =
        dimensions.findIndex(
          ([video_feed_width, video_feed_height]) =>
            video_feed_width === currWidth && video_feed_height === currHeight,
        ) || 0;
      const [video_feed_width, video_feed_height] =
        dimensions[idx + 1] || dimensions[0];
      await this.updateData({
        ...this.data,
        height: video_feed_height,
        width: video_feed_width,
      });
    },
    async decreaseDimension() {
      const currHeight = this.data?.height;
      const currWidth = this.data?.width;

      const idx =
        dimensions.findIndex(
          ([video_feed_width, video_feed_height]) =>
            video_feed_width === currWidth && video_feed_height === currHeight,
        ) || 0;
      const [video_feed_width, video_feed_height] =
        dimensions[idx - 1] || dimensions[dimensions.length - 1];
      await this.updateData({
        height: video_feed_height,
        width: video_feed_width,
      });
    },
    async capturePhoto() {
      const messager = useMessagerStore();
      try {
        const { data } = await axios.get<PhotoCaptureResponse>(
          "/api/camera/capture-photo",
        );

        return data.file;
      } catch (error) {
        messager.handleError(error, "Error capturing photo");
      }
    },
  },
});
