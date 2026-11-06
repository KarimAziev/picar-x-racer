import { defineStore } from "pinia";
import { useLocalStorage } from "@vueuse/core";
import { ref } from "vue";
import { robotApi } from "@/api";
import { useRobotStore } from "@/features/settings/stores";
import type { ServoData } from "@/features/settings/stores/robot";
import type {
  ServoName,
  ServoTuning,
} from "@/features/settings/components/calibration/servoTuning";

export type TuningModifier = "shiftKey" | "altKey" | "metaKey" | "ctrlKey";
export const tuningModifiers: Array<{ label: string; value: TuningModifier }> =
  [
    { label: "Shift", value: "shiftKey" },
    { label: "Alt / Option", value: "altKey" },
    { label: "Meta / Command", value: "metaKey" },
    { label: "Ctrl", value: "ctrlKey" },
  ];
export const useServoTuningStore = defineStore("servo-tuning", () => {
  const modifier = useLocalStorage<TuningModifier>(
    "servo-tuning-modifier",
    "shiftKey",
  );
  const pending = ref(false);
  const preview = async (
    servo: ServoName,
    settings: ServoTuning,
    angle: number,
  ) => {
    if (pending.value) return;
    pending.value = true;
    try {
      const result = await robotApi.post<Partial<ServoData>>(
        "px/api/settings/servo-tuning",
        { servo, settings, angle },
      );
      const robot = useRobotStore();
      const config = result[servo];
      if (config) {
        robot.partialData = result;
        robot.data[servo] = config;
      }
    } finally {
      pending.value = false;
    }
  };
  return { modifier, pending, preview };
});
