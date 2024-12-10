import { useMessagerStore } from "@/features/messager";
import { isNumber } from "@/util/guards";
import axios, { isAxiosError } from "axios";
import type { FileUploadUploaderEvent } from "primevue/fileupload";

export interface UploadStore {
  loading?: boolean;
}

export interface Params {
  url: string;
  onFinish?: () => void;
  onBeforeStart?: () => void;
}

export const useFileUploader = (params: Params) => {
  const messager = useMessagerStore();
  const { CancelToken } = axios;

  const source = CancelToken.source();

  const worker = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await axios.post(params.url, formData, {
        onUploadProgress: (progressEvent) => {
          if (isNumber(progressEvent.total)) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total,
            );
            if (progress < 100) {
              messager.info(`${progress}%`, {
                title: `Uploading ${file.name}`,
              });
            }
          }
        },
        cancelToken: source.token,
      });
      return response;
    } catch (error) {
      if (isAxiosError(error)) {
        const errorMessage =
          error.response?.data?.detail || error?.response?.statusText;
        messager.error(`Upload failed: ${errorMessage}`);
      } else {
        messager.handleError(error, "An error occurred during upload.");
      }
    }
  };

  const uploader = async (event: FileUploadUploaderEvent) => {
    const files = Array.isArray(event.files)
      ? event.files
      : event.files
        ? [event.files]
        : [];

    if (!files || files.length === 0) {
      messager.handleError("No file selected for upload.");
      return;
    }

    if (params.onBeforeStart) {
      params.onBeforeStart();
    }

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      await worker(file);
    }
    if (params.onFinish) {
      params.onFinish();
    }
  };
  return {
    uploader,
    cancel: source.cancel,
  };
};
