<template>
  <Field
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :label="label"
    :message="message"
    :layout="layout"
  >
    <ToggleSwitch
      v-tooltip="tooltip"
      :inputId="field"
      :pt="{ input: { id: field } }"
      :inputClass="inputClass"
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
import type { FieldLayout } from "@/ui/Field.vue";

export type Props = {
  modelValue?: any;
  invalid?: boolean;
  message?: string;
  label?: string;
  field?: string;
  fieldClassName?: string;
  labelClassName?: string;
  inputClass?: string;
  readonly?: boolean;
  disabled?: boolean;
  layout?: FieldLayout;
  tooltip?: string;
};
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
