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
import {
  InputNumberEmitsOptions,
  InputNumberProps,
} from "primevue/inputnumber";
import type { Props as FieldProps } from "@/ui/Field.vue";
import { isNumber } from "@/util/guards";
import { useControllerStore } from "@/features/controller/store";

import { useRobotStore } from "@/features/settings/stores";
import ServoInput from "@/features/settings/components/calibration/ServoInput.vue";

export interface Props extends FieldProps {
  modelValue?: any;
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
const otherAttrs: InputNumberProps = useAttrs();

const currentValue = ref(props.modelValue);

const commandActions = {
  cam_pan_servo: controllerStore.setCamPanAngle,
  cam_tilt_servo: controllerStore.setCamTiltAngle,
  steering_servo: controllerStore.setDirServoAngle,
};

const servoValues = {
  cam_pan_servo: controllerStore.camPan,
  cam_tilt_servo: controllerStore.camTilt,
  steering_servo: controllerStore.servoAngle,
};

const servosMap = {
  cam_pan_servo: robotStore.data.cam_pan_servo,
  cam_tilt_servo: robotStore.data.cam_tilt_servo,
  steering_servo: robotStore.data.steering_servo,
};

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
  () => props.field.split(".").shift() as keyof typeof servosMap,
);

const currentServoConfig = computed(() => servosMap[currentServoName.value]);

const currentServoValue = computed(() => servoValues[currentServoName.value]);

const commandAction = computed(() => commandActions[currentServoName.value]);

const handleServoMove = (value: number) => {
  commandAction.value(value);
};

const emit = defineEmits(["update:modelValue", "blur"]);

const onUpdate: InputNumberEmitsOptions["update:modelValue"] = (newValue) => {
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
