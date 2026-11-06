<template>
  <NumberInputField
    :messageClass="messageClass"
    :message="message"
    :label="label"
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
    :field="field"
    :tooltip="tooltip"
    :invalid="invalid"
    :disabled="readonly || disabled"
    v-model="currentValue"
    :step="step"
    :minFractionDigits="minFractionDigits"
    :maxFractionDigits="maxFractionDigits"
    v-bind="{ ...otherAttrs }"
    @update:model-value="onUpdate"
  ></NumberInputField>

  <ServoInput
    :field="`${currentServoName}-value`"
    @update:model-value="handleServoMove"
    :config="currentServoConfig"
    :value="currentServoValue"
    label="Current Servo Value"
  />
</template>

<script setup lang="ts">
import { ref, watch, useAttrs, computed } from "vue";
import NumberInputField from "@/ui/NumberInputField.vue";
import { InputNumberBlurEvent, InputNumberProps } from "primevue/inputnumber";
import type { Props as FieldProps } from "@/ui/Field.vue";
import { isNumber } from "@/util/guards";
import { useControllerStore } from "@/features/controller/store";

import { useRobotStore } from "@/features/settings/stores";
import ServoInput from "@/features/settings/components/calibration/ServoInput.vue";

export interface Props extends FieldProps {
  modelValue?: number | null;
  invalid?: boolean;
  field: string;
  minFractionDigits?: number;
  maxFractionDigits?: number;
  readonly?: boolean;
  disabled?: boolean;
  tooltip?: string;
  step?: number;
  exclusiveMinimum?: number;
  exclusiveMaximum?: number;
}

const props = withDefaults(defineProps<Props>(), {
  minFractionDigits: 1,
  maxFractionDigits: 1,
  useGrouping: false,
  allowEmpty: true,
  step: 0.1,
});

const robotStore = useRobotStore();
const controllerStore = useControllerStore();
const otherAttrs = useAttrs() as Partial<InputNumberProps>;

const currentValue = ref(props.modelValue);

const commandActions = {
  cam_pan_servo: controllerStore.setCamPanAngle,
  cam_tilt_servo: controllerStore.setCamTiltAngle,
  steering_servo: controllerStore.setDirServoAngle,
};

const servoValues = computed(() => ({
  cam_pan_servo: controllerStore.camPan,
  cam_tilt_servo: controllerStore.camTilt,
  steering_servo: controllerStore.servoAngle,
}));

const calibrationActionsMap = {
  "cam_pan_servo.calibration_offset": controllerStore.updateCamPanCali,
  "cam_tilt_servo.calibration_offset": controllerStore.updateCamTiltCali,
  "steering_servo.calibration_offset": controllerStore.updateServoDirCali,
};

const message = computed(() =>
  isNumber(currentValue.value) ? null : "Required",
);

const calibrationAction = computed(
  () =>
    calibrationActionsMap[props.field as keyof typeof calibrationActionsMap],
);
const currentServoName = computed(
  () => props.field.split(".").shift() as keyof typeof commandActions,
);

const currentServoConfig = computed(
  () => robotStore.data[currentServoName.value],
);

const currentServoValue = computed(
  () => servoValues.value[currentServoName.value],
);

const commandAction = computed(() => commandActions[currentServoName.value]);

const handleServoMove = (value: number) => {
  if (!controllerStore.calibrationMode)
    controllerStore.sendMessage({ action: "startServoTuning" });
  commandAction.value(value);
};

const emit = defineEmits<{
  "update:modelValue": [value: number | undefined];
  blur: [event: InputNumberBlurEvent];
}>();

const onUpdate = (newValue: number | undefined) => {
  if (isNumber(newValue)) {
    calibrationAction.value(newValue);
  }
  emit("update:modelValue", newValue);
};

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
  },
);
</script>
