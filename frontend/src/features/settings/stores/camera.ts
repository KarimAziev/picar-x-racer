import { defineStore } from "pinia";
import axios from "axios";
import type { TreeNode } from "primevue/treenode";
import { useMessagerStore } from "@/features/messager/store";
import { constrain } from "@/util/constrain";

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

export interface CameraSettings {
  /**
   * The ID or name of the camera device.
   */
  device?: string;

  /**
   * The width of the camera frame in pixels.
   */
  width?: number;

  /**
   * The height of the camera frame in pixels.
   */
  height?: number;

  /**
   * The number of frames per second the camera should capture.
   */
  fps?: number;

  /**
   * The format for the pixels (e.g., 'RGB', 'GRAY').
   */
  pixel_format?: string;
}

export interface DeviceSuboption extends TreeNode {
  device: string;
  size: string;
  fps: string;
  pixel_format: string;
}

export interface DeviceOption extends Pick<DeviceSuboption, "key" | "label"> {
  children: DeviceSuboption[];
}

export interface State {
  data: CameraSettings;
  loading: boolean;
  devices: DeviceOption[];
}

export const defaultState: State = {
  loading: false,
  data: {},
  devices: [],
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
          messager.handleError(error, `Error starting camera`);
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
        const { data } = await axios.get<{ devices: DeviceOption[] }>(
          "/api/camera/devices",
        );
        this.devices = data.devices;
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
  },
});
