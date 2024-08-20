import axios from "axios";

import { ControllerActionName } from "@/features/controller/store";
import { handleError } from "@/util/error";

export const READONLY_KEY = "Escape";

export const objectKeysToOptions = (
  obj: Record<string, string[]>,
  labelsMap?: Record<string, string>,
) =>
  Object.keys(obj).map((c) => ({
    value: c,
    label:
      (labelsMap && labelsMap[c]) ||
      c
        .trim()
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .split(" ")
        .map((v) => v[0].toUpperCase() + v.slice(1))
        .join(" "),
  }));

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

export const groupKeys = (data: Record<ControllerActionName, string[]>) =>
  Object.entries(data).reduce(
    (acc, [command, keys]) => {
      keys.forEach((k) => {
        acc[k] = command as ControllerActionName;
      });
      return acc;
    },
    {} as Record<string, ControllerActionName>,
  );
