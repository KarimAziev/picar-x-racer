import { MusicMode } from "@/features/music";

export const musicModeConfig = {
  [MusicMode.LOOP]: {
    tooltip: "Play all tracks on repeat continuously.",
    icon: "pi-sync",
  },
  [MusicMode.LOOP_ONE]: {
    tooltip: "Play the current track on repeat.",
    icon: "pi-arrow-right-arrow-left",
  },
  [MusicMode.QUEUE]: {
    tooltip: "Play all tracks once in order, without repeating.",
    icon: "pi-list",
  },
  [MusicMode.SINGLE]: {
    tooltip: "Play the current track once and stop playback.",
    icon: "pi-stop-circle",
  },
};
