<template>
  <NumberInputField
    label="Width"
    field="step-width"
    v-model="value.width"
    :disabled="loading"
    :loading="loading"
    :min="min_width"
    :max="max_width"
    :invalid="!!invalidData.width"
    :message="invalidData.width"
  />
  <NumberInputField
    label="Height"
    allowEmpty
    field="step-height"
    v-model="value.height"
    :disabled="loading"
    :loading="loading"
    :min="min_height"
    :invalid="!!invalidData.height"
    :message="invalidData.height"
  />
  <NumberInputField
    label="FPS"
    allowEmpty
    field="step-fps"
    v-model="value.fps"
    :disabled="loading"
    :loading="loading"
    :min="min_fps"
    :max="max_fps"
    :invalid="!!invalidData.fps"
    :message="invalidData.fps"
  />
  <Button :disabled="disabled || loading" @click="onUpdate">Submit</Button>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { useCameraStore } from "@/features/settings/stores";
import { StepwiseDeviceProps } from "@/features/settings/interface";
import NumberInputField from "@/ui/NumberInputField.vue";
import { inRange } from "@/util/number";
import { isNumber } from "@/util/guards";
import { Nullable } from "@/util/ts-helpers";

const camStore = useCameraStore();

const props = defineProps<StepwiseDeviceProps>();

const emit = defineEmits(["update:modelValue"]);
const value = defineModel<{
  width: Nullable<number>;
  height: Nullable<number>;
  fps: Nullable<number>;
}>({ required: true });

const invalidData = computed(() => {
  return Object.entries(value.value).reduce(
    (acc, [k, val]) => {
      const key = k as keyof (typeof value)["value"];
      const minVal = props[`min_${key}`];
      const maxVal = props[`max_${key}`];
      if (!isNumber(val)) {
        acc[key] = "Required";
      } else if (!inRange(val, minVal, maxVal)) {
        acc[key] = `Should be between ${minVal} and ${maxVal}`;
      }

      return acc;
    },
    {} as Record<keyof (typeof value)["value"], string>,
  );
});

const disabled = computed(() => !!Object.keys(invalidData.value).length);

const loading = computed(() => camStore.loading);

const onUpdate = () => {
  if (disabled.value) {
    return;
  }
  emit("update:modelValue", value.value);
};
</script>
