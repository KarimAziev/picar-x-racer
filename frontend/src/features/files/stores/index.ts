import { makeFileStore } from "@/features/files/store-fabric";
import { FilterMatchMode } from "@/features/files/enums";

export const useImageStore = makeFileStore("image");
export const useDataStore = makeFileStore("data");
export const useMusicStore = makeFileStore("music");
export const useVideoStore = makeFileStore("video");

export const useDetectionDataStore = makeFileStore(
  "data",
  {
    filters: {
      type: {
        value: null,
        match_mode: FilterMatchMode.IN,
      },
      file_suffixes: {
        value: ["_ncnn_model", ".pt", ".tflite", ".hef", ".onnx"],
        match_mode: FilterMatchMode.IN,
      },
    },
  },
  "detection-select",
);
