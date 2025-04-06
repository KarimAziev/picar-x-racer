<template>
  <Field
    :message="message"
    :label="label"
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
  >
    <ToggleSwitch
      v-tooltip="tooltip"
      :inputId="field"
      :pt="{ input: { id: field } }"
      :inputClass="inputClass"
      :class="class"
      v-model="currentValue"
      :invalid="invalid"
      :disabled="readonly || disabled"
      v-bind="otherAttrs"
      @update:model-value="onUpdate"
    />
  </Field>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs } from "vue";
import ToggleSwitch from "primevue/toggleswitch";
import type {
  ToggleSwitchProps,
  ToggleSwitchEmitsOptions,
} from "primevue/toggleswitch";
import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";

export interface Props extends FieldProps {
  modelValue?: any;
  invalid?: boolean;
  field?: string;
  inputClass?: string;
  readonly?: boolean;
  disabled?: boolean;
  tooltipHelp?: string;
  tooltip?: string;
  class?: string;
}
const props = defineProps<Props>();

const otherAttrs: ToggleSwitchProps = useAttrs();

const currentValue = ref(props.modelValue);

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
  },
);

const emit = defineEmits(["update:modelValue"]);

const onUpdate: ToggleSwitchEmitsOptions["update:modelValue"] = (newValue) => {
  emit("update:modelValue", newValue);
};
</script>
