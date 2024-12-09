import { useDetectionStore } from "@/features/detection";
import { useMessagerStore } from "@/features/messager";
import { isNumber } from "@/util/guards";
import axios, { isAxiosError } from "axios";
import type {
  FileUploadErrorEvent,
  FileUploadUploaderEvent,
} from "primevue/fileupload";

export const useModelUpload = () => {
  const detectionStore = useDetectionStore();

  const messager = useMessagerStore();

  const handleError = (event: FileUploadErrorEvent) => {
    messager.error(`Upload failed with status ${event.xhr.status}`);
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

    detectionStore.loading = true;

    const formData = new FormData();

    files.forEach((file: File) => {
      formData.append("file", file);
    });

    const mediaType = "data";

    try {
      const response = await axios.post(
        `/api/files/upload/${mediaType}`,
        formData,
        {
          onUploadProgress: (progressEvent) => {
            if (isNumber(progressEvent.total)) {
              const progress = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total,
              );
              messager.info(`${progress}%`, { title: `Uploading` });
            }
          },
        },
      );

      if (response.status === 200) {
        console.log("FETCHING models");
        await detectionStore.fetchModels();
        messager.info(`File uploaded successfully: ${response.data.filename}`);
      }
    } catch (error) {
      if (isAxiosError(error)) {
        const errorMessage =
          error.response?.data?.detail || error?.response?.statusText;
        messager.error(`Upload failed: ${errorMessage}`);
      } else {
        messager.handleError(error, "An error occurred during upload.");
      }
    } finally {
      detectionStore.loading = false;
    }
  };

  const handleUpload = (event: any) => {
    const { xhr } = event;

    if (xhr.status === 200) {
      console.log("refetching models");
      detectionStore.fetchModels();
    } else {
      messager.error(`Upload failed with status ${xhr.status}`);
    }
  };
  return {
    handleUpload,
    uploader,
    handleError,
  };
};
