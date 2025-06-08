<template>
  <Field
    :message="message"
    :label="label"
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
    :messageClass="messageClass"
  >
    <CycleButton
      v-bind="buttonProps"
      @update:model-value="onUpdate"
      :class="contentClass"
    />
  </Field>
</template>

<script setup lang="ts">
import type { ButtonProps } from "primevue/button";
import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";
import CycleButton from "@/ui/CycleButton.vue";
import { omit, pick } from "@/util/obj";
import { computed } from "vue";

export type BtnProps = Pick<
  ButtonProps,
  | "outlined"
  | "severity"
  | "icon"
  | "iconPos"
  | "size"
  | "variant"
  | "fluid"
  | "text"
  | "rounded"
  | "raised"
  | "badgeSeverity"
  | "badgeClass"
  | "badge"
>;

export interface Props extends FieldProps {
  contentClass?: string;
  options?: number[];
  modelValue?: number | null;
  buttonLabel?: string;
  btnProps?: BtnProps;
}

const buttonProps = computed(() => ({
  ...pick(["options", "buttonLabel", "modelValue"], props),
  ...omit(
    [
      "message",
      "btnProps",
      "label",
      "fieldClassName",
      "labelClassName",
      "layout",
      "tooltipHelp",
    ],
    props || {},
  ),
}));

const emit = defineEmits(["update:modelValue"]);

const props = withDefaults(defineProps<Props>(), {
  options: () => [1, -1],
  buttonLabel: "Reverse",
});

const onUpdate = (newValue: number) => {
  emit("update:modelValue", newValue);
};
</script>
