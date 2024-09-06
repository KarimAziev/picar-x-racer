import { defineStore } from "pinia";
import axios from "axios";
import { useMessagerStore } from "@/features/messager/store";

export interface CameraOpenRequestParams {
  width?: number;
  height?: number;
  fps?: number;
}
export interface State {
  data: CameraOpenRequestParams;
  loading: boolean;
  cancelTokenSource?: AbortController;
}

const defaultState: State = {
  loading: false,
  data: {},
  cancelTokenSource: undefined,
};

export const useStore = defineStore("camera", {
  state: () => ({ ...defaultState }),
  actions: {
    async cameraStart(data?: CameraOpenRequestParams) {
      const messager = useMessagerStore();

      if (this.cancelTokenSource) {
        this.cancelTokenSource.abort();
      }

      const cancelTokenSource = new AbortController();
      this.cancelTokenSource = cancelTokenSource;

      try {
        this.loading = true;
        const response = await axios.post<CameraOpenRequestParams>(
          "/api/start-camera",
          data || this.data,
          { signal: cancelTokenSource.signal },
        );

        this.data = response.data;
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
  },
});
