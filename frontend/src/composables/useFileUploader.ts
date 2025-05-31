import { useMessagerStore } from "@/features/messager";
import { isNumber } from "@/util/guards";
import axios, { isAxiosError, Canceler } from "axios";
import type { FileUploadUploaderEvent } from "primevue/fileupload";
import { ref, unref } from "vue";
import type { ComputedRef } from "vue";
import { Nullable } from "@/util/ts-helpers";
import { appApi } from "@/api";

export interface UploadStore {
  loading?: boolean;
}

export interface Params {
  url: string;
  dir?: ComputedRef<Nullable<string>> | Nullable<string>;
  onFinish?: (files: File[], dir?: Nullable<string>) => void;
  onBeforeStart?: (files: File[], dir?: Nullable<string>) => void;
  onFinishFile?: (file: File, dir?: Nullable<string>) => void;
  onBeforeFileStart?: (file: File, dir?: Nullable<string>) => void;
  onProgress?: (file: File, progress: number, dir?: Nullable<string>) => void;
}

export const useFileUploader = (params: Params) => {
  const messager = useMessagerStore();
  const { CancelToken } = axios;

  const cancelSources = ref<
    Record<string, { dir?: Nullable<string>; cancel: Canceler }>
  >({});

  const worker = async (file: File, currentDir?: Nullable<string>) => {
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (currentDir) {
        formData.append("dir", currentDir);
      }
      const source = CancelToken.source();
      const filepath = [currentDir, file.name].filter((v) => v).join("/");

      cancelSources.value[filepath] = {
        dir: currentDir,
        cancel: () => source.cancel(),
      };
      const progressFn = messager.makeProgress(`Uploading ${filepath}`);
      const response = await appApi.post(params.url, formData, {
        onUploadProgress: (progressEvent) => {
          if (isNumber(progressEvent.total)) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total,
            );

            if (params.onProgress) {
              params.onProgress(file, progress, currentDir);
            }

            if (progress < 100) {
              progressFn(progress);
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
    const dir = unref(params.dir);
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
      params.onBeforeStart(files, dir);
    }

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (params.onBeforeFileStart) {
        params.onBeforeFileStart(file, dir);
      }
      await worker(file, dir);
      if (params.onFinishFile) {
        params.onFinishFile(file, dir);
      }
    }
    cancelSources.value = {};
    if (params.onFinish) {
      params.onFinish(files);
    }
  };
  return {
    uploader,
    cancelSources,
  };
};
