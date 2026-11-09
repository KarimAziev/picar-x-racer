<template>
  <Dialog
    :visible="visible"
    header="Servo & motor tuning"
    class="settings-popup w-[92vw] max-w-[640px] font-sans"
    modal
    :draggable="false"
    :closable="!tuning.pending"
    :close-on-escape="!tuning.pending"
    @update:visible="handleVisibility"
  >
    <CalibrationPanel :id="id" embedded />
    <template #footer>
      <Button
        label="Close tuning"
        outlined
        :disabled="tuning.pending"
        @click="close"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Dialog from "primevue/dialog";
import Button from "primevue/button";
import { useControllerStore } from "@/features/controller/store";
import { usePopupStore } from "@/features/settings/stores";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";
import CalibrationPanel from "@/features/settings/components/calibration/CalibrationPanel.vue";

defineProps<{ id: string }>();

const controllerStore = useControllerStore();
const popupStore = usePopupStore();
const tuning = useServoTuningStore();
const dismissed = ref(false);
const visible = computed(
  () =>
    controllerStore.calibrationMode && !popupStore.isOpen && !dismissed.value,
);
const close = () => {
  if (tuning.pending || dismissed.value) return;
  dismissed.value = true;
  controllerStore.sendMessage({ action: "stopServoTuning" });
};
const handleVisibility = (value: boolean) => {
  if (!value) close();
};
watch(
  () => controllerStore.calibrationMode,
  () => {
    dismissed.value = false;
  },
);
</script>
