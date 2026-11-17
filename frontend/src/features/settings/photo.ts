import type { CameraSettings } from "@/features/settings/interface";

export interface PhotoPreset {
  id: string;
  name: string;
  camera: CameraSettings & { device: string; width: number; height: number };
  format: ".jpg" | ".png";
  quality: number;
  rotation: number;
  enhance_mode: string | null;
  settle_seconds: number;
}

export interface PhotoSettings {
  presets: PhotoPreset[];
  selected_preset_id: string | null;
}
