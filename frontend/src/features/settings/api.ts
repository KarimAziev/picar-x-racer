import axios from "axios";
import { handleError } from "@/util/error";
import { APIMediaType } from "@/features/settings/interface";

export const downloadFile = async (mediaType: string, fileName: string) => {
  try {
    const response = await axios.get(`/api/download/${mediaType}/${fileName}`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");

    link.href = url;
    link.setAttribute("download", fileName);
    document.body.appendChild(link);
    link.click();
  } catch (error) {
    handleError(error, `Error downloading ${mediaType} file`);
  }
};

export const removeFile = async (mediaType: APIMediaType, file: string) => {
  try {
    await axios.delete(`/api/remove_file/${mediaType}`, {
      data: { filename: file },
    });
  } catch (error) {
    handleError(error, `Error removing ${file}`);
  }
};
