<template>
  <Field
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :label="label"
    :message="message"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
  >
    <RadioComponentSwitcher
      class="flex items-center gap-2"
      :options="options"
      v-bind="{ ...otherAttrs, ...props }"
    />
  </Field>
</template>

<script setup lang="ts">
import { useAttrs, computed } from "vue";
import InputText from "primevue/inputtext";
import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";
import { isNumber, isString } from "@/util/guards";
import { InputNumber } from "primevue";

import { defineComponentOptions, GetComponentProps } from "@/util/vue-helpers";
import RadioComponentSwitcher from "@/ui/RadioComponentSwitcher.vue";
import { isHexString, hexToDecimal, decimalToHexString } from "@/util/hex";
import { parseTrailingNumber } from "@/util/number";
import { extractLetterPrefix } from "@/util/str";

export interface Props extends FieldProps {
  modelValue?: any;
  invalid?: boolean;
  label?: string;
  field?: string;
  inputClassName?: string;
  readonly?: boolean;
  disabled?: boolean;
  tooltip?: string;
  hex?: boolean;
  integerProps?: GetComponentProps<typeof InputNumber>;
  stringProps?: GetComponentProps<typeof InputText>;
}

const props = defineProps<Props>();
const options = computed(() =>
  defineComponentOptions(
    {
      integer: InputNumber,
      string: InputText,
    },
    {
      integer: {
        pt: { pcInput: { id: props.field } },
        label: "Integer",
        pred: isNumber,
        comp: InputNumber,
        convertValueOnSwitch: props.hex,
        convertToValue: (val?: string) =>
          !isString(val)
            ? val
            : isHexString(val)
              ? hexToDecimal(val)
              : parseTrailingNumber(val),
        props: {
          inputId: props.field,
          class: props.inputClassName,
          invalid: props.invalid,
          disabled: props.disabled || props.readonly,
          showButtons: true,
          pt: {
            pcInput: { id: props.field },
          },
          ...props.integerProps,
        },
      },
      string: {
        pt: { pcInput: { id: props.field } },
        label: props.hex ? "Hex" : "String",
        pred: isString,
        comp: InputText,
        convertValueOnSwitch: props.hex,
        convertToValue: (val?: number, prevValue?: string) => {
          if (!isNumber(val)) {
            return val;
          }
          if (props.hex) {
            return decimalToHexString(val);
          }
          if (isString(prevValue)) {
            const prefix = extractLetterPrefix(prevValue);
            console.log("prefix", prefix, "prevValue", prevValue);
            return `${prefix || ""}${val}`;
          }

          return `${val}`;
        },
        props: {
          inputId: props.field,
          class: props.inputClassName,
          invalid: props.invalid,
          disabled: props.disabled || props.readonly,
          pt: {
            pcInput: { id: props.field },
          },
          ...props.stringProps,
        },
      },
    },
  ),
);
const otherAttrs = useAttrs();
</script>
