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
    <CalibrationPanel ref="panel" :id="id" embedded />
    <template #footer>
      <CalibrationActions :saving="panel?.saving" @save="panel?.save()">
        <Button
          label="Close tuning"
          size="small"
          outlined
          :disabled="tuning.pending"
          @click="close"
        />
      </CalibrationActions>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from "vue";
import Dialog from "primevue/dialog";
import Button from "primevue/button";
import { useControllerStore } from "@/features/controller/store";
import { usePopupStore } from "@/features/settings/stores";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";
import CalibrationPanel from "@/features/settings/components/calibration/CalibrationPanel.vue";
import CalibrationActions from "@/features/settings/components/calibration/CalibrationActions.vue";

defineProps<{ id: string }>();

const panel = useTemplateRef("panel");

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
