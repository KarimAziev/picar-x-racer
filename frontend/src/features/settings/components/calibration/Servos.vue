<template>
  <div class="flex flex-col gap-2">
    <ServoTuning
      ref="servos"
      v-for="name in availableServos"
      :key="name"
      :name="name"
    />
  </div>
</template>
<script setup lang="ts">
import { computed, useTemplateRef } from "vue";
import { useRobotStore } from "@/features/settings/stores";
import ServoTuning from "@/features/settings/components/calibration/ServoTuning.vue";
import { servoNames } from "@/features/settings/components/calibration/servoTuning";
const robot = useRobotStore();
const availableServos = computed(() =>
  servoNames.filter((name) => robot.data[name]),
);
const servos = useTemplateRef("servos");
const applyDrafts = async () => {
  return (servos.value ?? []).reduce<Promise<boolean>>(
    async (previous, servo) => {
      if (!(await previous)) return false;
      return servo?.applyDraft() ?? true;
    },
    Promise.resolve(true),
  );
};
defineExpose({ applyDrafts });
</script>
