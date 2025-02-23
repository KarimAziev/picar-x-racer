import { useStore as useSettingsStore } from "@/features/settings/stores/settings";
import { useStore as useImageStore } from "@/features/settings/stores/images";
import { useStore as usePopupStore } from "@/features/settings/stores/popup";
import { useStore as useBatteryStore } from "@/features/settings/stores/battery";
import { useStore as useDistanceStore } from "@/features/settings/stores/distance";
import { useStore as useCameraStore } from "@/features/settings/stores/camera";
import { useStore as useStreamStore } from "@/features/settings/stores/stream";
import { useStore as useThemeStore } from "@/features/settings/stores/theme";
import { useStore as useFPSStore } from "@/features/settings/stores/fps";
import { useStore as useTTSStore } from "@/features/settings/stores/tts";
import { useStore as useRobotStore } from "@/features/settings/stores/robot";
import { useStore as useVideoStore } from "@/features/settings/stores/video";

export {
  useImageStore,
  useSettingsStore,
  usePopupStore,
  useBatteryStore,
  useDistanceStore,
  useCameraStore,
  useStreamStore,
  useThemeStore,
  useFPSStore,
  useTTSStore,
  useRobotStore,
  useVideoStore,
};
