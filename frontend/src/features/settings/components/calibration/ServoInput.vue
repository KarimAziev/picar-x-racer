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
    :min="config.min_angle"
    :max="config.max_angle"
    :invalid="invalid"
    :disabled="readonly || disabled"
    v-model="currentValue"
    :step="1"
    :useGrouping="useGrouping"
    :allowEmpty="allowEmpty"
    v-bind="{ ...otherAttrs }"
    @update:model-value="onUpdate"
  ></NumberInputField>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs, computed } from "vue";

import NumberInputField from "@/ui/NumberInputField.vue";
import {
  InputNumberEmitsOptions,
  InputNumberProps,
} from "primevue/inputnumber";
import { Props as FieldProps } from "@/ui/Field.vue";
import { isNumber } from "@/util/guards";
import { ServoConfig } from "@/features/settings/stores/robot";

export interface Props extends FieldProps {
  value?: any;
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
  config: ServoConfig;
  useGrouping?: boolean;
  allowEmpty?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  useGrouping: false,
  allowEmpty: false,
});

const otherAttrs: InputNumberProps = useAttrs();

const currentValue = ref(props.value);

const message = computed(() =>
  isNumber(currentValue.value) ? null : "Required",
);

const emit = defineEmits(["update:modelValue"]);

const onUpdate: InputNumberEmitsOptions["update:modelValue"] = (newValue) => {
  if (isNumber(newValue)) {
    emit("update:modelValue", newValue);
  }
};

watch(
  () => props.value,
  (newVal) => {
    currentValue.value = newVal;
  },
);
</script>
