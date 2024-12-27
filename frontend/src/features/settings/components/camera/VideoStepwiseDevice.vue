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

const camStore = useCameraStore();

defineProps<DeviceStepwise>();

const emit = defineEmits(["update:modelValue"]);

const fps = ref(30);
const width = ref<number | undefined>();
const height = ref<number | undefined>();

const loading = computed(() => camStore.loading);

const onUpdate = () => {
  if (!height.value || !width.value) {
    return;
  }
  emit("update:modelValue", {
    height: roundNumber(height.value),
    width: roundNumber(width.value),
    fps: roundNumber(fps.value),
  });
};
</script>
<style scoped lang="scss"></style>
