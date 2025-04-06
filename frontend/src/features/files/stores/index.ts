import { makeFileStore, defaultState } from "@/features/files/store-fabric";
import { FilterMatchMode } from "@/features/files/enums";
import { cloneDeep } from "@/util/obj";

export const useImageStore = makeFileStore("image", "image");
export const useDataStore = makeFileStore("data", "data");
export const useMusicFileStore = makeFileStore("audio-files", "music");
export const useVideoStore = makeFileStore("video", "video");

export const useDetectionDataStore = makeFileStore("detection-select", "data", {
  filters: {
    ...cloneDeep(defaultState.filters),
    file_suffixes: {
      value: ["_ncnn_model", ".pt", ".tflite", ".hef", ".onnx"],
      match_mode: FilterMatchMode.IN,
    },
  },
});

export const useFileExplorer = makeFileStore("file-explorer", null, {
  root_dir: "~/",
});
