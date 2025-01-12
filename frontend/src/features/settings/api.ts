import axios from "axios";
import {
  APIMediaType,
  RemoveFileResponse,
} from "@/features/settings/interface";
import { retrieveError } from "@/util/error";

export const downloadFile = async (mediaType: string, fileName: string) => {
  const response = await axios.get(
    `/api/files/download/${mediaType}/${fileName}`,
    {
      responseType: "blob",
    },
  );
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
) => {
  try {
    const response = await axios.post(
      `/api/files/download/archive`,
      {
        media_type: mediaType,
        filenames: fileNames,
      },
      {
        responseType: "blob",
      },
    );

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");

    const archiveName = `${mediaType}_files_archive.zip`;

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
  axios.delete<RemoveFileResponse>(`/api/files/remove/${mediaType}/${file}`);

export const batchRemoveFiles = (
  mediaType: APIMediaType,
  filenames: string[],
) =>
  axios.post<RemoveFileResponse[]>(`/api/files/remove-batch/${mediaType}`, {
    filenames,
  });
