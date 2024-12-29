<template>
  <NumberInputField
    label="Width"
    field="step-width"
    v-model="width"
    :disabled="loading"
    :loading="loading"
    :min="min_width"
    :max="max_width"
    :invalid="!width"
    :message="!width ? 'Required' : null"
  />
  <NumberInputField
    label="Height"
    allowEmpty
    field="step-height"
    v-model="height"
    :disabled="loading"
    :loading="loading"
    :min="min_height"
    :invalid="!height"
    :max="max_height"
    :message="!height ? 'Required' : null"
  />
  <NumberInputField
    label="FPS"
    allowEmpty
    field="step-fps"
    v-model="fps"
    :disabled="loading"
    :loading="loading"
    :min="min_fps"
    :max="max_fps"
  />
  <Button :disabled="disabled || loading" @click="onUpdate">Submit</Button>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";

import { useCameraStore } from "@/features/settings/stores";
import { StepwiseDeviceProps } from "@/features/settings/interface";
import NumberInputField from "@/ui/NumberInputField.vue";
import { roundNumber } from "@/util/number";
import { useDebounce } from "@/composables/useDebounce";
import { constrain } from "@/util/constrain";

const camStore = useCameraStore();

const props = defineProps<StepwiseDeviceProps>();

const emit = defineEmits(["update:modelValue"]);

const fps = ref(
  constrain(props.min_fps, props.max_fps, camStore.data.fps || 30),
);
const width = ref<number | undefined>(
  camStore.data.width
    ? constrain(props.min_width, props.max_width, camStore.data.width || 640)
    : undefined,
);
const height = ref<number | undefined>(
  camStore.data.height
    ? constrain(props.min_width, props.max_width, camStore.data.height)
    : undefined,
);

const disabled = computed(() => !height.value || !width.value || !fps.value);

const loading = computed(() => camStore.loading);

const onUpdate = useDebounce(() => {
  if (!height.value || !width.value || !fps.value) {
    return;
  }
  emit("update:modelValue", {
    height: roundNumber(height.value),
    width: roundNumber(width.value),
    fps: roundNumber(fps.value),
  });
}, 1000);
</script>
<style scoped lang="scss"></style>
