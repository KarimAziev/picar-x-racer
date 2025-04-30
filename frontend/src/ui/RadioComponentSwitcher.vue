<template>
  <div v-for="opt in options" :key="opt.value" :class="class">
    <RadioButton
      v-model="valueType"
      :name="field"
      :value="opt.value"
      @update:model-value="handleUpdateValueType"
    />
    <span>{{ opt.label }}</span>
    <TooltipHelp :tooltip="opt.tooltip" v-if="opt.tooltip" />
  </div>
  <div v-for="opt in options" :key="opt.value" :class="class">
    <component
      v-if="opt.value === valueType"
      :is="opt.comp"
      @update:model-value="onUpdate"
      v-model="data[valueType]"
      v-bind="{ ...otherAttrs, ...(opt.props as any) }"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, useAttrs } from "vue";
import RadioButton from "primevue/radiobutton";
import type { Props as FieldProps } from "@/ui/Field.vue";
import { Option } from "@/util/vue-helpers";
import TooltipHelp from "@/ui/TooltipHelp.vue";

export interface Props extends FieldProps {
  modelValue?: any;
  field?: string;
  options: Option[];
  class?: string;
}

const props = defineProps<Props>();
const otherAttrs = useAttrs();

const optionsToData = (value: any, prevData?: Record<string, any>) =>
  props.options.reduce(
    (acc, opt) => {
      const key = opt.value;
      acc[key] = opt.pred(value)
        ? value
        : opt.convertToValue
          ? opt.convertToValue(value, (prevData || {})[opt.value])
          : undefined;
      return acc;
    },
    {} as Record<string, any>,
  );

const data = ref(optionsToData(props.modelValue));

const findValueTypeByValue = (value: any) =>
  (props.options.find((opt) => opt.pred(value)) || props.options[0]).value;

const findOptionByType = (type: string) =>
  props.options.find((opt) => opt.value === type);

const prevType = ref(findValueTypeByValue(props.modelValue));

const valueType = ref(prevType.value);

const handleUpdateValueType = (optionType: string) => {
  const opt = findOptionByType(optionType);
  const currVal = data.value[prevType.value];
  if (opt && opt.convertValueOnSwitch && opt.convertToValue) {
    data.value[optionType] = opt.convertToValue(currVal, data.value);
  }
  prevType.value = optionType;
};

watch(
  () => props.modelValue,
  (newVal) => {
    prevType.value = valueType.value;
    valueType.value = findValueTypeByValue(newVal);
    data.value = optionsToData(newVal, data.value);
  },
);

const emit = defineEmits(["update:modelValue", "value-change"]);

const onUpdate = (newValue?: string | number) => {
  emit("update:modelValue", newValue);
};
</script>
