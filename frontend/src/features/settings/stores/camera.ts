import axios from "axios";
import { defineStore } from "pinia";
import { useMessagerStore } from "@/features/messager";
import { isStepwiseDevice } from "@/features/settings/components/camera/util";
import { constrain } from "@/util/constrain";
import { isNumber } from "@/util/guards";
import {
  Device,
  CameraSettings,
  DeviceStepwise,
  DiscreteDevice,
} from "@/features/settings/interface";
import { retrieveError } from "@/util/error";
import { appApi } from "@/api";

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
const FPS_EPSILON = 1e-6;

const roundFps = (value: number) => Math.round(value * 1000) / 1000;

const uniqueSortedFps = (values: number[]) =>
  Array.from(new Set(values.map(roundFps))).sort((a, b) => a - b);

const matchesCameraMode = (device: Device, settings: CameraSettings) => {
  if (!settings.device || device.device !== settings.device) {
    return false;
  }

  if (
    (settings.pixel_format &&
      device.pixel_format &&
      device.pixel_format !== settings.pixel_format) ||
    (settings.media_type &&
      device.media_type &&
      device.media_type !== settings.media_type)
  ) {
    return false;
  }

  if (isStepwiseDevice(device)) {
    return (
      isNumber(settings.width) &&
      isNumber(settings.height) &&
      settings.width >= device.min_width &&
      settings.width <= device.max_width &&
      settings.height >= device.min_height &&
      settings.height <= device.max_height
    );
  }

  return device.width === settings.width && device.height === settings.height;
};

const stepwiseFpsValues = (device: DeviceStepwise) => {
  const minFps = roundFps(device.min_fps);
  const maxFps = roundFps(device.max_fps);
  const step = device.fps_step || maxFps - minFps;

  if (Math.abs(maxFps - minFps) < FPS_EPSILON || step <= FPS_EPSILON) {
    return [maxFps];
  }

  const values = [minFps];
  let current = minFps + step;
  while (current < maxFps - FPS_EPSILON) {
    values.push(roundFps(current));
    current += step;
  }
  values.push(maxFps);
  return uniqueSortedFps(values);
};

const supportedFpsValues = (devices: Device[], settings: CameraSettings) => {
  const matchingModes = devices.filter((device) =>
    matchesCameraMode(device, settings),
  );

  const discreteFps = matchingModes
    .filter(
      (device): device is DiscreteDevice =>
        !isStepwiseDevice(device) && isNumber(device.fps),
    )
    .map((device) => device.fps as number);

  if (discreteFps.length > 0) {
    return uniqueSortedFps(discreteFps);
  }

  const stepwiseMode = matchingModes.find(isStepwiseDevice);
  return stepwiseMode ? stepwiseFpsValues(stepwiseMode) : [];
};

const nextSupportedFps = (
  values: number[],
  currentValue: number,
  direction: 1 | -1,
) => {
  if (values.length === 0) {
    return currentValue;
  }

  if (direction > 0) {
    return values.find((value) => value > currentValue + FPS_EPSILON)
      ?? values[values.length - 1];
  }

  return [...values]
    .reverse()
    .find((value) => value < currentValue - FPS_EPSILON) ?? values[0];
};

export interface PhotoCaptureResponse {
  file: string;
}

export interface State {
  data: CameraSettings;
  loading: boolean;
  devices: Device[];
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

        this.data = await appApi.post<CameraSettings>(
          "/api/camera/settings",
          payload || this.data,
        );
        this.error = null;
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
        const data = await appApi.get<CameraSettings>("/api/camera/settings");
        this.data = data;
      } catch (error) {
        messager.handleError(error, "Error fetching camera settings");
      } finally {
        this.loading = false;
      }
    },

    async fetchDevices() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const data = await appApi.get<{ devices: Device[] }>(
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
      const nextFps = nextSupportedFps(
        supportedFpsValues(this.devices, this.data),
        video_feed_fps,
        1,
      );
      await this.updateData({
        ...this.data,
        fps: constrain(10, MAX_FPS, nextFps),
      });
    },
    async decreaseFPS() {
      const video_feed_fps = this.data.fps || 30;
      const nextFps = nextSupportedFps(
        supportedFpsValues(this.devices, this.data),
        video_feed_fps,
        -1,
      );
      await this.updateData({
        ...this.data,
        fps: constrain(5, MAX_FPS, nextFps),
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
        const data = await appApi.post<PhotoCaptureResponse>(
          "/api/camera/capture-photo",
        );

        return data.file;
      } catch (error) {
        messager.handleError(error, "Error capturing photo");
      }
    },
  },
});
