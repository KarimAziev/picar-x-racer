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
  <Field
    class="relative w-full h-52"
    labelClassName="text-center p-4"
    label="Try"
  >
    <div ref="joystickZone"></div>
  </Field>
</template>

<script setup lang="ts">
import {
  ref,
  watch,
  useAttrs,
  computed,
  useTemplateRef,
  onMounted,
  onBeforeUnmount,
} from "vue";
import type { JoystickManagerOptions } from "nipplejs";
import nipplejs from "nipplejs";
import NumberInputField from "@/ui/NumberInputField.vue";
import {
  InputNumberEmitsOptions,
  InputNumberProps,
} from "primevue/inputnumber";
import Field, { Props as FieldProps } from "@/ui/Field.vue";
import { isNumber } from "@/util/guards";
import { useControllerStore } from "@/features/controller/store";

import { roundToNearestTen, inRange } from "@/util/number";
import { constrain } from "@/util/constrain";

import { useRobotStore } from "@/features/settings/stores";
import {
  MIN_JOYSTICK_ANGLE,
  HALF_CIRCLE_MAX,
} from "@/features/joystick/composables/useJoysticManager";
import { debounce } from "@/util/debounce";

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
  allowEmpty: false,
  step: 0.1,
});

const robotStore = useRobotStore();
const controllerStore = useControllerStore();
const otherAttrs: InputNumberProps = useAttrs();

const joystickZone = useTemplateRef("joystickZone");
const currentValue = ref(props.modelValue);

const commandActions = {
  cam_pan_servo: controllerStore.setCamPanAngle,
  cam_tilt_servo: controllerStore.setCamTiltAngle,
  steering_servo: controllerStore.setDirServoAngle,
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

const currentServo = computed(
  () => servosMap[props.field.split(".").shift() as keyof typeof servosMap],
);

const commandAction = computed(
  () =>
    commandActions[
      props.field.split(".").shift() as keyof typeof commandActions
    ],
);

const joystickManager = ref<nipplejs.JoystickManager | null>(null);

const handleJoystickMove = (data: nipplejs.JoystickOutputData) => {
  const servo = currentServo.value;

  const { angle } = data;

  const direction = angle.degree;

  const isPlainForward = inRange(
    direction,
    MIN_JOYSTICK_ANGLE,
    HALF_CIRCLE_MAX,
  );

  const minServoAngle = servo.min_angle;
  const maxServoAngle = servo.max_angle;

  const directionWithinRange =
    (isPlainForward ? direction : direction - HALF_CIRCLE_MAX) -
    MIN_JOYSTICK_ANGLE;

  const value =
    (directionWithinRange * (minServoAngle - maxServoAngle)) /
      (HALF_CIRCLE_MAX - MIN_JOYSTICK_ANGLE) +
    maxServoAngle;

  const clampedValue = constrain(minServoAngle, maxServoAngle, value);

  const roundedValue = roundToNearestTen(clampedValue);
  commandAction.value(roundedValue);
};

const handleDestroyJoysticManager = () => {
  if (joystickManager.value) {
    joystickManager.value.destroy();
  }
};

const handleJoystickEnd = (_evt: nipplejs.EventData) => {
  commandAction.value(0);
};

const handleCreateJoysticManager = (params?: JoystickManagerOptions) => {
  if (joystickZone.value) {
    const styles = getComputedStyle(document.documentElement);
    const color = styles.getPropertyValue("--color-text").trim();
    joystickManager.value = nipplejs.create({
      zone: joystickZone.value!,
      size: 80,
      dynamicPage: true,
      mode: "static",
      position: { top: "50%", left: "50%" },
      color: color,
      ...params,
    });

    joystickManager.value.on("move", (_event, data) => {
      handleJoystickMove(data);
    });

    joystickManager.value.on("end", handleJoystickEnd);
  }
};

const restartJoysticManager = debounce(() => {
  handleDestroyJoysticManager();
  handleCreateJoysticManager();
}, 500);

onMounted(() => {
  window.addEventListener("resize", restartJoysticManager);
  window.addEventListener("update-primary-palette", restartJoysticManager);
  window.addEventListener("orientationchange", restartJoysticManager);
  handleCreateJoysticManager();
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", restartJoysticManager);
  window.removeEventListener("update-primary-palette", restartJoysticManager);
  window.removeEventListener("orientationchange", restartJoysticManager);
  handleDestroyJoysticManager();
});

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
