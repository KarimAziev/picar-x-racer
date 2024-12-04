import { useStore as useSettingsStore } from "@/features/settings/stores/settings";
import { useStore as useMusicStore } from "@/features/settings/stores/music";
import { useStore as useImageStore } from "@/features/settings/stores/images";
import { useStore as usePopupStore } from "@/features/settings/stores/popup";
import { useStore as useBatteryStore } from "@/features/settings/stores/battery";
import { useStore as useCalibrationStore } from "@/features/settings/stores/calibration";
import { useStore as useDistanceStore } from "@/features/settings/stores/distance";
import { useStore as useCameraStore } from "@/features/settings/stores/camera";
import { useStore as useStreamStore } from "@/features/settings/stores/stream";
import { useStore as useDetectionStore } from "@/features/settings/stores/detection";

export {
  useImageStore,
  useMusicStore,
  useSettingsStore,
  usePopupStore,
  useBatteryStore,
  useCalibrationStore,
  useDistanceStore,
  useCameraStore,
  useDetectionStore,
  useStreamStore,
};
