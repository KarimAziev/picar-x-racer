import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager/store";
import { constrain } from "@/util/constrain";
import { wait } from "@/util/wait";

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

export interface CameraOpenRequestParams {
  width?: number;
  height?: number;
  fps?: number;
}
export interface State {
  data: CameraOpenRequestParams;
  dimensions: { width: number; height: number } | null;
  loading: boolean;
  cancelTokenSource?: AbortController;
}

const defaultState: State = {
  loading: false,
  data: {},
  dimensions: null,
  cancelTokenSource: undefined,
};

export const useStore = defineStore("camera", {
  state: () => ({ ...defaultState }),
  actions: {
    async cameraStart(payload?: CameraOpenRequestParams) {
      const messager = useMessagerStore();

      if (this.cancelTokenSource) {
        this.cancelTokenSource.abort();
      }

      const cancelTokenSource = new AbortController();
      this.cancelTokenSource = cancelTokenSource;

      try {
        this.loading = true;
        const { data } = await axios.post<CameraOpenRequestParams>(
          "/api/start-camera",
          payload || this.data,
          { signal: cancelTokenSource.signal },
        );
        await wait(500);
        const { fps, width, height } = data;
        const size = width && height ? `${width}x${height}` : "";
        this.data = data;
        messager.info(`Started camera with FPS: ${fps} ${size}`);
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
    async cameraClose() {
      const messager = useMessagerStore();

      // Cancel any pending request
      if (this.cancelTokenSource) {
        this.cancelTokenSource.abort();
      }

      // Create a new cancel token source for the new request
      const cancelTokenSource = new AbortController();
      this.cancelTokenSource = cancelTokenSource;

      try {
        this.loading = true;
        const response = await axios.get<CameraOpenRequestParams>(
          `/api/close-camera`,
          { signal: cancelTokenSource.signal },
        );

        this.data = response.data;
      } catch (error) {
        if (axios.isCancel(error)) {
          console.log("Request canceled:", error.message);
        } else {
          messager.handleError(error, `Error closing camera`);
        }
      } finally {
        this.loading = false;
        // Nullify the cancel token source after request completes
        this.cancelTokenSource = undefined;
      }
      return this.data;
    },
    async fetchDimensions() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const { data } = await axios.get("api/frame-dimensions");
        const { height, width } = data;
        this.dimensions = data;
        messager.info(`Dimensions: width ${width}, height ${height}`);
      } catch (error) {
        messager.handleError(error, "Error fetching settings");
      } finally {
        this.loading = false;
      }
    },
    async increaseFPS() {
      const fps = this.data.fps || 30;
      await this.cameraStart({
        ...this.data,
        fps: constrain(10, MAX_FPS, fps + 10),
      });
    },
    async decreaseFPS() {
      const fps = this.data.fps || 30;
      await this.cameraStart({
        ...this.data,
        fps: constrain(5, MAX_FPS, Math.max(5, fps - 10)),
      });
    },
    async increaseDimension() {
      const currHeight = this.data?.height;
      const currWidth = this.data?.width;
      const fps = this.data.fps || 30;
      const idx =
        dimensions.findIndex(
          ([width, height]) => width === currWidth && height === currHeight,
        ) || 0;
      const [width, height] = dimensions[idx + 1] || dimensions[0];
      await this.cameraStart({ fps, height, width });
    },
    async decreaseDimension() {
      const currHeight = this.data?.height;
      const currWidth = this.data?.width;
      const fps = this.data.fps || 30;
      const idx =
        dimensions.findIndex(
          ([width, height]) => width === currWidth && height === currHeight,
        ) || 0;
      const [width, height] =
        dimensions[idx - 1] || dimensions[dimensions.length - 1];
      await this.cameraStart({ fps, height, width });
    },
  },
});
