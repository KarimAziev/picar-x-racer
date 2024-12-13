import { useControllerStore } from "@/features/controller/store";

export type APIMediaType = "image" | "sound" | "music" | "data";

export type ControllerStore = ReturnType<typeof useControllerStore>;

export interface ValueLabelOption {
  value: string;
  label: string;
}
