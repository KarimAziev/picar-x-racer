import axios from "axios";
import { APIMediaType } from "@/features/settings/interface";

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

export const removeFile = (mediaType: APIMediaType, file: string) =>
  axios.delete(`/api/files/remove/${mediaType}/${file}`);
