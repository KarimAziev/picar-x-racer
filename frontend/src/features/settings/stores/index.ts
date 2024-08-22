import { useStore as useSettingsStore } from "@/features/settings/stores/settings";
import { useStore as useMusicStore } from "@/features/settings/stores/music";
import { useStore as useSoundStore } from "@/features/settings/stores/sounds";
import { useStore as useImageStore } from "@/features/settings/stores/images";
import { useStore as usePopupStore } from "@/features/settings/stores/popup";
import { useStore as useBatteryStore } from "@/features/settings/stores/battery";

export {
  useImageStore,
  useMusicStore,
  useSoundStore,
  useSettingsStore,
  usePopupStore,
  useBatteryStore,
};
