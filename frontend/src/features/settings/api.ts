import {
  APIMediaType,
  RemoveFileResponse,
} from "@/features/settings/interface";
import { isString } from "@/util/guards";
import { appApi } from "@/api";

export const downloadFile = async (
  mediaType: string,
  fileName: string,
  onProgress?: (progress: number) => void,
) => {
  const response = await appApi.get<Blob>(
    `/api/files/download/${mediaType}?filename=${encodeURIComponent(fileName)}`,
    {
      responseType: "blob",
      onDownloadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total,
          );

          if (onProgress) {
            onProgress(percentCompleted);
          }
        }
      },
    },
  );
  const url = window.URL.createObjectURL(new Blob([response]));
  const link = document.createElement("a");

  link.href = url;
  link.setAttribute("download", fileName);
  document.body.appendChild(link);
  link.click();
};

export const extractContentDispositionFilename = (
  contentDisposition?: string,
) => {
  if (!isString(contentDisposition)) {
    return;
  }
  const filenameMatch = contentDisposition.match(
    /filename\*?=["']?(?:UTF-8'')?([^;"']+)["']?/,
  );
  if (filenameMatch && filenameMatch[1]) {
    return decodeURIComponent(filenameMatch[1]);
  }
};

export const removeFile = (mediaType: APIMediaType, file: string) =>
  appApi.delete<RemoveFileResponse>(
    `/api/files/remove/${mediaType}?filename=${encodeURIComponent(file)}`,
  );

export const batchRemoveFiles = (
  mediaType: APIMediaType,
  filenames: string[],
) =>
  appApi.post<RemoveFileResponse[]>(`/api/files/remove-batch/${mediaType}`, {
    filenames,
  });
