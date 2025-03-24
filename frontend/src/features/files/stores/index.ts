import { makeFileStore, defaultState } from "@/features/files/store-fabric";
import { FilterMatchMode } from "@/features/files/enums";
import { cloneDeep } from "@/util/obj";

export const useImageStore = makeFileStore("image");
export const useDataStore = makeFileStore("data");
export const useMusicFileStore = makeFileStore("music", {}, "audio-files");
export const useVideoStore = makeFileStore("video");

export const useDetectionDataStore = makeFileStore(
  "data",
  {
    filters: {
      ...cloneDeep(defaultState.filters),
      file_suffixes: {
        value: ["_ncnn_model", ".pt", ".tflite", ".hef", ".onnx"],
        match_mode: FilterMatchMode.IN,
      },
    },
  },
  "detection-select",
);
