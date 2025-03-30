import axios from "axios";
import { APIMediaType, BatchFileStatus } from "@/features/files/interface";
import { retrieveError } from "@/util/error";
import {
  extractContentDispositionFilename,
  mapConcat,
} from "@/features/files/util";
import { Nullable } from "@/util/ts-helpers";

export const makeImagePreviewURL = (
  path: string,
  mediaType: Nullable<APIMediaType>,
) =>
  `${mapConcat(
    ["/api/files/preview-image", mediaType],
    "/",
  )}?filename=${encodeURIComponent(path)}`;

export const makeVideoPreviewURL = (
  path: string,
  mediaType: Nullable<APIMediaType>,
) =>
  `${mapConcat(
    ["/api/files/preview-video", mediaType],
    "/",
  )}?filename=${encodeURIComponent(path)}`;

export const makeVideoURL = (path: string, mediaType: Nullable<APIMediaType>) =>
  `${mapConcat(
    ["/api/files/video-stream", mediaType],
    "/",
  )}?filename=${encodeURIComponent(path)}`;

export const makeAudioURL = (path: string, mediaType: Nullable<APIMediaType>) =>
  `${mapConcat(
    ["/api/files/audio-stream", mediaType],
    "/",
  )}?filename=${encodeURIComponent(path)}`;

export const makeUploadURL = (mediaType: Nullable<APIMediaType>) =>
  mapConcat(["/api/files/upload", mediaType], "/");

export const makeDownloadURL = (
  fileName: string,
  mediaType: Nullable<APIMediaType>,
) =>
  `${mapConcat(
    ["/api/files/download", mediaType],
    "/",
  )}?filename=${encodeURIComponent(fileName)}`;

export const makeSaveURL = (mediaType: Nullable<APIMediaType>) =>
  mapConcat(["/api/files/write", mediaType], "/");

export const downloadFile = async (
  fileName: string,
  mediaType: Nullable<APIMediaType>,
  onProgress?: (progress: number) => void,
) => {
  const response = await axios.get(makeDownloadURL(fileName, mediaType), {
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
  fileNames: string[],
  aliasDir?: Nullable<string>,
  downloadName?: string,
  onProgress?: (progress: number) => void,
) => {
  try {
    const response = await axios.post<Blob>(
      mapConcat(["/api/files/download/archive", aliasDir], "/"),
      {
        archive_name: downloadName || aliasDir || "files_archive.zip",
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
      ) || [aliasDir, `files_archive.zip`].filter((v) => v).join("_");

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

export const removeFile = (file: string) =>
  axios.delete<BatchFileStatus>(
    `/api/files/remove?filename=${encodeURIComponent(file)}`,
  );

export const batchRemoveFiles = (
  filenames: string[],
  mediaType: Nullable<APIMediaType>,
) =>
  axios.post<BatchFileStatus[]>(
    mapConcat(["/api/files/remove-batch", mediaType], "/"),
    {
      filenames,
    },
  );

export const batchMoveFiles = (
  mediaType: Nullable<APIMediaType>,
  filenames: string[],
  dir: string,
) =>
  axios.post<BatchFileStatus[]>(
    mapConcat(["/api/files/move", mediaType], "/"),
    {
      filenames,
      dir,
    },
  );

export const renameFile = (filename: string, new_name: string) =>
  axios.post<BatchFileStatus[]>("/api/files/rename", {
    filename,
    new_name,
  });

export const makeDir = (filename: string, mediaType: Nullable<APIMediaType>) =>
  axios.post<BatchFileStatus[]>(
    mapConcat(["/api/files/mkdir", mediaType], "/"),
    {
      filename,
    },
  );
