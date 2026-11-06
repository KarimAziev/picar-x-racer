<template>
  <Fieldset :id="`servo-tuning-${name}`" :legend="servoLabels[name]" collapsed>
    <p v-if="!config.enabled" class="text-sm">
      Enable this servo in advanced hardware settings to tune it.
    </p>
    <div v-else class="flex flex-col gap-3">
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <ServoInput
          :field="`${name}-current`"
          label="Current servo value (°)"
          :config="draftConfig"
          :value="currentAngle"
          :disabled="blocked"
          @update:model-value="move"
        />
        <NumberInputField
          :field="`${name}-offset`"
          label="Center offset (°)"
          :model-value="config.calibration_offset"
          :step="0.1"
          :min="-180"
          :max="180"
          :allow-empty="false"
          :disabled="tuning.pending"
          @update:model-value="updateOffset"
        />
      </div>
      <ToggleSwitchField
        :field="`${name}-reverse`"
        label="Reverse direction"
        v-model="draft.reverse"
        :disabled="tuning.pending"
        tooltip-help="Reverse logical servo movement. Apply or move the current servo value to test it; Save tuning keeps it."
      />
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <NumberInputField
          v-for="field in tuningFields"
          :key="field.key"
          :field="`${name}-${field.key}`"
          :label="field.label"
          :model-value="draft[field.key]"
          :min="field.min"
          :max="field.max"
          :step="field.step"
          :allow-empty="false"
          :disabled="tuning.pending"
          input-class-name="w-full"
          @update:model-value="updateField(field.key, $event)"
        />
      </div>
      <p class="text-sm text-muted-color">
        Travel limits bound movement. Pulse widths and their measured angles
        define the pulse calibration.
      </p>
      <div class="flex flex-wrap items-center gap-2">
        <Button
          size="small"
          outlined
          label="Apply at current angle"
          :disabled="blocked || !hasDraftChanges"
          @click="applyDraft"
        />
        <span
          v-if="hasDraftChanges"
          class="text-sm text-muted-color"
          role="status"
        >
          Unapplied field edits. Apply before testing with keyboard shortcuts.
        </span>
      </div>
      <NumberInputField
        :field="`${name}-test`"
        label="Test angle (°)"
        v-model="testAngle"
        :min="minimum"
        :max="maximum"
        :disabled="tuning.pending"
        :allow-empty="false"
      />
      <p v-if="validation || error" role="alert" class="text-sm text-red-500">
        {{ validation || error }}
      </p>
      <div class="flex flex-wrap gap-2">
        <Button
          size="small"
          outlined
          label="Apply & test minimum"
          :disabled="blocked"
          @click="preview(minimum)"
        />
        <Button
          size="small"
          outlined
          label="Apply & center"
          :disabled="blocked"
          @click="preview(Math.min(maximum, Math.max(minimum, 0)))"
        />
        <Button
          size="small"
          outlined
          label="Apply & test maximum"
          :disabled="blocked"
          @click="preview(maximum)"
        />
        <Button
          size="small"
          label="Apply & test angle"
          :disabled="blocked || !isNumber(testAngle)"
          @click="preview(testAngle)"
        />
        <Button
          size="small"
          text
          label="Discard field edits"
          :disabled="tuning.pending"
          @click="discardEdits"
        />
      </div>
      <p class="text-sm text-muted-color">
        Current servo value and Apply & test use the fields above without
        saving. Apply at current angle activates them for keyboard shortcuts,
        using the nearest travel limit if needed. Save tuning keeps the
        adjustments and leaves tuning open; Stop keyboard tuning ends the
        session.
      </p>
    </div>
  </Fieldset>
</template>
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Button from "primevue/button";
import Fieldset from "@/ui/Fieldset.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import NumberInputField from "@/ui/NumberInputField.vue";
import ServoInput from "@/features/settings/components/calibration/ServoInput.vue";
import { useRobotStore } from "@/features/settings/stores";
import { useControllerStore } from "@/features/controller/store";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";
import {
  getServoTuning,
  servoLabels,
  servoTuningError,
  tuningFields,
  type ServoName,
  type NumericTuningField,
} from "@/features/settings/components/calibration/servoTuning";
import { isNumber } from "@/util/guards";
import { robotSettingsError } from "@/features/settings/robotErrors";
const props = defineProps<{ name: ServoName }>();
const robot = useRobotStore();
const controller = useControllerStore();
const tuning = useServoTuningStore();
const config = computed(() => robot.data[props.name]);
const draft = ref(getServoTuning(config.value));
const draftConfig = computed(() => ({ ...config.value, ...draft.value }));
const hasDraftChanges = computed(() => {
  const applied = getServoTuning(config.value);
  return (
    draft.value.reverse !== applied.reverse ||
    tuningFields.some(({ key }) => draft.value[key] !== applied[key])
  );
});
const error = ref("");
const testAngle = ref<number | undefined>(0);
const invalidFields = ref(new Set<NumericTuningField>());
const validation = computed(() =>
  invalidFields.value.size
    ? "Complete every tuning field before applying settings."
    : servoTuningError(draft.value),
);
const discardEdits = () => {
  draft.value = getServoTuning(config.value);
  invalidFields.value.clear();
};
const blocked = computed(
  () => !!validation.value || tuning.pending || !controller.model?.connected,
);
const minimum = computed(() =>
  draft.value.reverse ? -draft.value.max_angle : draft.value.min_angle,
);
const maximum = computed(() =>
  draft.value.reverse ? -draft.value.min_angle : draft.value.max_angle,
);
const currentAngle = computed(
  () =>
    ({
      steering_servo: controller.servoAngle,
      cam_pan_servo: controller.camPan,
      cam_tilt_servo: controller.camTilt,
    })[props.name],
);
const move = (angle: number) => {
  if (blocked.value) return;
  if (hasDraftChanges.value) {
    void preview(angle);
    return;
  }
  if (!controller.calibrationMode)
    controller.sendMessage({ action: "startServoTuning" });
  ({
    steering_servo: controller.setDirServoAngle,
    cam_pan_servo: controller.setCamPanAngle,
    cam_tilt_servo: controller.setCamTiltAngle,
  })[props.name](angle);
};
const updateOffset = (value: number | undefined) => {
  if (isNumber(value))
    ({
      steering_servo: controller.updateServoDirCali,
      cam_pan_servo: controller.updateCamPanCali,
      cam_tilt_servo: controller.updateCamTiltCali,
    })[props.name](value);
};
const updateField = (key: NumericTuningField, value: number | undefined) => {
  if (isNumber(value)) {
    draft.value[key] = value;
    invalidFields.value.delete(key);
  } else {
    invalidFields.value.add(key);
  }
};
watch(
  () => getServoTuning(config.value),
  (value, previous) => {
    if (draft.value.reverse === previous.reverse)
      draft.value.reverse = value.reverse;
    tuningFields.forEach(({ key }) => {
      if (draft.value[key] === previous[key]) draft.value[key] = value[key];
    });
  },
);
const preview = async (angle: number | undefined) => {
  if (blocked.value || !isNumber(angle)) return false;
  error.value = "";
  try {
    await tuning.preview(props.name, { ...draft.value }, angle);
    return true;
  } catch (cause) {
    error.value = robotSettingsError(cause, robot.config);
    return false;
  }
};
const applyDraft = async () => {
  if (validation.value) return false;
  if (!hasDraftChanges.value) return true;
  return preview(
    Math.min(maximum.value, Math.max(minimum.value, currentAngle.value)),
  );
};
defineExpose({ applyDraft });
</script>
