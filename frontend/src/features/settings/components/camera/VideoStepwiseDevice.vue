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
    @update:model-value="onUpdate"
  />
  <NumberInputField
    label="Height"
    field="step-height"
    v-model="height"
    :disabled="loading"
    :loading="loading"
    :min="min_height"
    :invalid="!height"
    :max="max_height"
    :message="!height ? 'Required' : null"
    @update:model-value="onUpdate"
  />
  <NumberInputField
    label="FPS"
    field="step-fps"
    v-model="fps"
    :disabled="loading"
    :loading="loading"
    :min="1"
    :max="90"
    @update:model-value="onUpdate"
  />
</template>

<script setup lang="ts">
import { ref, computed } from "vue";

import { useCameraStore } from "@/features/settings/stores";
import { DeviceStepwise } from "@/features/settings/interface";
import NumberInputField from "@/ui/NumberInputField.vue";
import { roundNumber } from "@/util/number";
import { useDebounce } from "@/composables/useDebounce";

const camStore = useCameraStore();

const props = defineProps<DeviceStepwise>();

const emit = defineEmits(["update:modelValue"]);

const fps = ref(camStore.data.fps || 30);
const width = ref<number | undefined>(
  props.max_width >= (camStore.data.width || 0) &&
    props.min_width <= (camStore.data.width || 0)
    ? camStore.data.width
    : undefined,
);
const height = ref<number | undefined>(
  props.max_height >= (camStore.data.height || 0) &&
    props.min_height <= (camStore.data.height || 0)
    ? camStore.data.height
    : undefined,
);

const loading = computed(() => camStore.loading);

const onUpdate = useDebounce(() => {
  if (!height.value || !width.value) {
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
