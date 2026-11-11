<template>
  <component
    :is="embedded ? 'div' : Fieldset"
    v-bind="
      embedded
        ? {}
        : { legend: 'Servo & motor tuning', toggleable: true, collapsed }
    "
    :id="id"
  >
    <p class="mb-3 text-sm text-muted-color">
      Adjust servo centers, travel, pulse calibration, and motor direction. Use
      guided motion calibration for measured geometry and driving response.
      Tuning pauses driving until you stop tuning. Save tuning keeps your
      adjustments while leaving the session open.
    </p>
    <SelectField
      label="Offset shortcut modifier"
      v-model="tuning.modifier"
      :options="tuningModifiers"
      option-label="label"
      option-value="value"
      class="mb-3"
    />
    <p class="mb-3 text-sm text-muted-color">
      In keyboard tuning mode, servo shortcuts move the servo; hold the selected
      modifier with the same shortcut to adjust its center offset. Steering
      stays at the tested angle when released. Keyboard controls pause while
      editing fields.
    </p>
    <slot></slot>
    <div class="flex flex-col gap-y-2">
      <Servos ref="servos" />
      <Motors />
      <CalibrationActions
        v-if="!embedded"
        :saving="saving"
        @save="handleSaveClick"
      />
    </div>
  </component>
</template>

<script setup lang="ts">
import { ref, useTemplateRef } from "vue";
import { useControllerStore } from "@/features/controller/store";
import Servos from "@/features/settings/components/calibration/Servos.vue";
import Motors from "@/features/settings/components/calibration/Motors.vue";
import SelectField from "@/ui/SelectField.vue";
import {
  useServoTuningStore,
  tuningModifiers,
} from "@/features/settings/stores/servoTuning";
import Fieldset from "@/ui/Fieldset.vue";
import CalibrationActions from "@/features/settings/components/calibration/CalibrationActions.vue";

const props = defineProps<{
  handleSave?: () => void;
  collapsed?: boolean;
  embedded?: boolean;
  id: string;
}>();

const servos = useTemplateRef("servos");
const saving = ref(false);
const handleSaveClick = async () => {
  if (saving.value || tuning.pending) return;
  saving.value = true;
  try {
    if (!(await servos.value?.applyDrafts())) return;
    if (props.handleSave) {
      props.handleSave();
    } else {
      controllerStore.saveCalibration();
    }
  } finally {
    saving.value = false;
  }
};

const controllerStore = useControllerStore();
const tuning = useServoTuningStore();

defineExpose({ save: handleSaveClick, saving });
</script>
