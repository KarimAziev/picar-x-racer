import { useControllerStore } from "@/features/controller/store";

export type APIMediaType = "image" | "sound" | "music";

export type ControllerStore = ReturnType<typeof useControllerStore>;
