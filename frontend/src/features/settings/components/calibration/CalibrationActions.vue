<template>
  <div class="flex w-full flex-wrap items-center justify-end gap-2">
    <Button
      severity="danger"
      size="small"
      text
      label="Reset offsets & directions"
      @click="controller.resetCalibration"
    />
    <Button
      size="small"
      outlined
      :label="
        controller.calibrationMode
          ? 'Stop keyboard tuning'
          : 'Start keyboard tuning'
      "
      @click="controller.toggleCalibration"
    />
    <Button
      size="small"
      label="Save tuning"
      :disabled="saving || tuning.pending"
      @click="$emit('save')"
    />
    <slot />
  </div>
</template>

<script setup lang="ts">
import Button from "primevue/button";
import { useControllerStore } from "@/features/controller/store";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";

defineProps<{ saving?: boolean }>();
defineEmits<{ save: [] }>();

const controller = useControllerStore();
const tuning = useServoTuningStore();
</script>
