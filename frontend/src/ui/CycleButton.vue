<template>
  <div class="flex items-center select-none gap-2">
    <InputText v-if="isString(modelValue)" :modelValue="modelValue" readonly />
    <InputNumber
      v-else-if="isNumber(modelValue)"
      :modelValue="modelValue"
      readonly
    />
    <span v-else>
      {{ modelValue }}
    </span>
    <Button
      class="flex-1 font-bold"
      :disabled="!options || !options.length || disabled"
      :readonly="readonly"
      @click="onUpdate"
      v-bind="buttonProps"
      :label="buttonLabel"
    ></Button>
  </div>
</template>

<script setup lang="ts" generic="Value">
import { cycleValue } from "@/util/cycleValue";
import { isNil, isNumber, isString } from "@/util/guards";
import type { ButtonProps } from "primevue/button";
import { computed } from "vue";
import { pick } from "@/util/obj";

interface Props {
  modelValue?: Value;
  readonly?: boolean;
  disabled?: boolean;
  tooltip?: string;
  tooltipHelp?: string;
  findValue?: (value: Value) => boolean;
  options?: any[];
  direction?: number;
  buttonLabel?: string;
  severity?: ButtonProps["severity"];
  icon?: ButtonProps["icon"];
  iconPos?: ButtonProps["iconPos"];
  size?: ButtonProps["size"];
  variant?: ButtonProps["variant"];
  fluid?: ButtonProps["fluid"];
  text?: ButtonProps["text"];
  rounded?: ButtonProps["rounded"];
  raised?: ButtonProps["raised"];
  badgeSeverity?: ButtonProps["badgeSeverity"];
  badgeClass?: ButtonProps["badgeClass"];
  badge?: ButtonProps["badge"];
  outlined?: ButtonProps["outlined"];
}

const buttonProps = computed(() =>
  pick(
    [
      "severity",
      "icon",
      "iconPos",
      "size",
      "variant",
      "fluid",
      "text",
      "rounded",
      "raised",
      "badgeSeverity",
      "badgeClass",
      "badge",
      "outlined",
    ],
    props,
  ),
);

const emit = defineEmits(["update:modelValue"]);

const props = withDefaults(defineProps<Props>(), {
  direction: 1,
  size: "small",
  outlined: true,
});
const onUpdate = () => {
  if (!props.options) {
    return;
  }
  const newValue = isNil(props.modelValue)
    ? props.options[0]
    : cycleValue(
        props.findValue || props.modelValue,
        props.options,
        props.direction,
      );

  emit("update:modelValue", newValue);
};
</script>
