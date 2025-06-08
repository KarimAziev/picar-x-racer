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
    <span
      class="wrapper p-inputnumber p-component p-inputwrapper p-inputwrapper-filled p-inputnumber-stacked"
    >
      <span
        class="p-inputtext p-component p-inputnumber-input"
        :class="{ disabled: !!disabled }"
        v-tooltip="tooltip"
      >
        {{ currentValue }}
      </span>
      <span class="p-inputnumber-button-group">
        <Button
          class="p-inputnumber-button p-inputnumber-increment-button up p-0"
          @click="handleInc"
          :readonly="loading"
          :disabled="disabled"
          size="small"
          icon="pi pi-angle-up"
        />
        <Button
          class="p-inputnumber-button p-inputnumber-decrement-button down p-0"
          @click="handleDec"
          :readonly="loading"
          :disabled="disabled"
          size="small"
          icon="pi pi-angle-down"
        />
      </span>
    </span>
    <slot></slot>
  </Field>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";
import { isNumber } from "@/util/guards";

export interface Props extends FieldProps {
  step: number;
  loading?: boolean;
  max?: number;
  min?: number;
  modelValue?: any;
  invalid?: boolean;
  field?: string;
  readonly?: boolean;
  disabled?: boolean;
  normalizeValue?: (val: number) => number;
  tooltip?: string;
}

const props = defineProps<Props>();

const currentValue = ref(props.modelValue);

watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
  },
);

const emit = defineEmits(["update:modelValue"]);

const handleUpdate = (val: number) => {
  if (isNumber(props.max) && val > props.max) {
    while (val > props.max) {
      val -= props.step;
    }
  }

  if (isNumber(props.min) && val < props.min) {
    while (val < props.min) {
      val += props.step;
    }
  }

  currentValue.value =
    props.normalizeValue && isNumber(val) ? props.normalizeValue(val) : val;

  emit("update:modelValue", currentValue.value);
};

const handleInc = () => {
  handleUpdate(currentValue.value + props.step);
};
const handleDec = () => {
  handleUpdate(currentValue.value - props.step);
};
</script>
<style scoped lang="scss">
.wrapper {
  position: relative;
}
.disabled {
  opacity: 1;
  background: var(--p-inputtext-disabled-background);
  color: var(--p-inputtext-disabled-color);
}

button {
  border-radius: 0;

  color: var(--p-select-dropdown-color);
  margin: 0px;
  border: none;

  &:not(:disabled):hover {
    border: none;
    background: var(--p-inputnumber-button-hover-background);
    color: var(--p-inputnumber-button-hover-color);
  }
}
.p-inputnumber {
  display: inline-flex;
  position: relative;
}
.p-inputnumber-button {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  cursor: pointer;
  background: var(--p-inputnumber-button-background);
  color: var(--p-inputnumber-button-color);
  width: var(--p-inputnumber-button-width);
  transition:
    background var(--p-inputnumber-transition-duration),
    color var(--p-inputnumber-transition-duration),
    border-color var(--p-inputnumber-transition-duration),
    outline-color var(--p-inputnumber-transition-duration);
}
.p-inputnumber-button:hover {
  background: var(--p-inputnumber-button-hover-background);
  color: var(--p-inputnumber-button-hover-color);
}
.p-inputnumber-button:active {
  background: var(--p-inputnumber-button-active-background);
  color: var(--p-inputnumber-button-active-color);
}
.p-inputnumber-stacked .p-inputnumber-button {
  position: relative;
  border: 0 none;
}
.p-inputnumber-stacked .p-inputnumber-button-group {
  display: flex;
  flex-direction: column;
  position: absolute;
  inset-block-start: 1px;
  inset-inline-end: 1px;
  height: calc(100% - 2px);
  z-index: 1;
}
.p-inputnumber-stacked .p-inputnumber-increment-button {
  padding: 0;
  border-start-end-radius: calc(
    var(--p-inputnumber-button-border-radius) - 1px
  );
}
.p-inputnumber-stacked .p-inputnumber-decrement-button {
  padding: 0;
  border-end-end-radius: calc(var(--p-inputnumber-button-border-radius) - 1px);
}
:deep(.pi-angle-up) {
  position: relative;
  top: 2px;
}

.p-inputnumber-stacked .p-inputnumber-button {
  flex: 1 1 auto;
  border: 0 none;
}
.p-inputnumber-horizontal .p-inputnumber-button {
  border: 1px solid var(--p-inputnumber-button-border-color);
}
.p-inputnumber-horizontal .p-inputnumber-button:hover {
  border-color: var(--p-inputnumber-button-hover-border-color);
}
.p-inputnumber-horizontal .p-inputnumber-button:active {
  border-color: var(--p-inputnumber-button-active-border-color);
}
.p-inputnumber-horizontal .p-inputnumber-increment-button {
  order: 3;
  border-start-end-radius: var(--p-inputnumber-button-border-radius);
  border-end-end-radius: var(--p-inputnumber-button-border-radius);
  border-inline-start: 0 none;
}
.p-inputnumber-horizontal .p-inputnumber-input {
  order: 2;
  border-radius: 0;
}
.p-inputnumber-horizontal .p-inputnumber-decrement-button {
  order: 1;
  border-start-start-radius: var(--p-inputnumber-button-border-radius);
  border-end-start-radius: var(--p-inputnumber-button-border-radius);
  border-inline-end: 0 none;
}
.p-floatlabel:has(.p-inputnumber-horizontal) label {
  margin-inline-start: var(--p-inputnumber-button-width);
}
.p-inputnumber-vertical {
  flex-direction: column;
}
.p-inputnumber-vertical .p-inputnumber-button {
  border: 1px solid var(--p-inputnumber-button-border-color);
  /* padding: var(--p-inputnumber-button-vertical-padding); */
}
.p-inputnumber-vertical .p-inputnumber-button:hover {
  border-color: var(--p-inputnumber-button-hover-border-color);
}
.p-inputnumber-vertical .p-inputnumber-button:active {
  border-color: var(--p-inputnumber-button-active-border-color);
}
.p-inputnumber-vertical .p-inputnumber-increment-button {
  order: 1;
  border-start-start-radius: var(--p-inputnumber-button-border-radius);
  border-start-end-radius: var(--p-inputnumber-button-border-radius);
  width: 100%;
  border-block-end: 0 none;
}
.p-inputnumber-vertical .p-inputnumber-input {
  order: 2;
  border-radius: 0;
  text-align: center;
}
.p-inputnumber-vertical .p-inputnumber-decrement-button {
  order: 3;
  border-end-start-radius: var(--p-inputnumber-button-border-radius);
  border-end-end-radius: var(--p-inputnumber-button-border-radius);
  width: 100%;
  border-block-start: 0 none;
}
.p-inputnumber-input {
  flex: 1 1 auto;
}
.p-inputnumber-fluid {
  width: 100%;
}
.p-inputnumber-fluid .p-inputnumber-input {
  width: 1%;
}
.p-inputnumber-fluid.p-inputnumber-vertical .p-inputnumber-input {
  width: 100%;
}
.p-inputnumber:has(.p-inputtext-sm) .p-inputnumber-button .p-icon {
  font-size: var(--p-form-field-sm-font-size);
  width: var(--p-form-field-sm-font-size);
  height: var(--p-form-field-sm-font-size);
}
.p-inputnumber:has(.p-inputtext-lg) .p-inputnumber-button .p-icon {
  font-size: var(--p-form-field-lg-font-size);
  width: var(--p-form-field-lg-font-size);
  height: var(--p-form-field-lg-font-size);
}
</style>
