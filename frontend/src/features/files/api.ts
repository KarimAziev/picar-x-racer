import axios from "axios";
import { APIMediaType, BatchFileStatus } from "@/features/files/interface";
import { retrieveError } from "@/util/error";
import { extractContentDispositionFilename } from "@/features/files/util";

export const makeImagePreviewURL = (path: string, mediaType: APIMediaType) =>
  `/api/files/preview-image/${mediaType}?filename=${encodeURIComponent(path)}`;
export const makeVideoPreviewURL = (path: string, mediaType: APIMediaType) =>
  `/api/files/preview-video/${mediaType}?filename=${encodeURIComponent(path)}`;
export const makeVideoURL = (path: string, mediaType: APIMediaType) =>
  `/api/files/stream/${mediaType}?filename=${encodeURIComponent(path)}`;

export const makeUploadURL = (mediaType: APIMediaType) =>
  `/api/files/upload/${mediaType}`;

export const makeDownloadURL = (mediaType: APIMediaType, fileName: string) =>
  `/api/files/download/${mediaType}?filename=${encodeURIComponent(fileName)}`;

export const makeSaveURL = (mediaType: APIMediaType) =>
  `/api/files/save/${mediaType}`;

export const downloadFile = async (
  mediaType: APIMediaType,
  fileName: string,
  onProgress?: (progress: number) => void,
) => {
  const response = await axios.get(makeDownloadURL(mediaType, fileName), {
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
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");

  link.href = url;

  link.setAttribute("download", fileName);
  document.body.appendChild(link);
  link.click();
};

export const downloadFilesAsArchive = async (
  mediaType: string,
  fileNames: string[],
  onProgress?: (progress: number) => void,
) => {
  try {
    const response = await axios.post<Blob>(
      `/api/files/download/archive`,
      {
        media_type: mediaType,
        filenames: fileNames,
      },
      {
        responseType: "blob",
        headers: {
          Accept: "application/zip",
          "Content-Type": "application/json",
        },
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

    const archiveName =
      extractContentDispositionFilename(
        response.headers["content-disposition"],
      ) || `${mediaType}_files_archive.zip`;

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");

    link.href = url;
    link.setAttribute("download", archiveName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    const errData = retrieveError(error);
    throw new Error(errData.text.length > 0 ? errData.text : errData.title);
  }
};

export const removeFile = (mediaType: APIMediaType, file: string) =>
  axios.delete<BatchFileStatus>(
    `/api/files/remove/${mediaType}?filename=${encodeURIComponent(file)}`,
  );

export const batchRemoveFiles = (
  mediaType: APIMediaType,
  filenames: string[],
) =>
  axios.post<BatchFileStatus[]>(`/api/files/remove-batch/${mediaType}`, {
    filenames,
  });

export const batchMoveFiles = (
  mediaType: APIMediaType,
  filenames: string[],
  dir: string,
) =>
  axios.post<BatchFileStatus[]>(`/api/files/move/${mediaType}`, {
    filenames,
    dir,
  });

export const renameFile = (
  mediaType: APIMediaType,
  filename: string,
  new_name: string,
) =>
  axios.post<BatchFileStatus[]>(`/api/files/rename/${mediaType}`, {
    filename,
    new_name,
  });

export const makeDir = (mediaType: APIMediaType, filename: string) =>
  axios.post<BatchFileStatus[]>(`/api/files/mkdir/${mediaType}`, {
    filename,
  });

export const loadTextFile = async (
  mediaType: APIMediaType,
  fileName: string,
  onProgress?: (progress: number) => void,
) =>
  await axios.get<string>(makeDownloadURL(mediaType, fileName), {
    responseType: "text",
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
  });
