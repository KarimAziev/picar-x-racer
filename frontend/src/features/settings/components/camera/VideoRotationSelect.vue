<template>
  <div>
    <div>Video rotation</div>
    <div class="flex gap-2">
      <div
        v-for="option in rotationOptions"
        :key="option.label"
        class="flex items-center gap-2"
      >
        <RadioButton
          v-model="streamStore.data.rotation"
          :inputId="option.label"
          name="image-rotation"
          :value="option.value"
          @update:model-value="updateStreamParams"
        />
        <label :for="option.label">{{ option.label }}</label>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore, useStreamStore } from "@/features/settings/stores";
import { useAsyncDebounce } from "@/composables/useDebounce";
import { rotationOptions } from "@/features/settings/components/camera/config";

const settingsStore = useSettingsStore();

const streamStore = useStreamStore();

const updateStreamParams = useAsyncDebounce(async () => {
  settingsStore.data.stream = streamStore.data;
  await streamStore.updateData(streamStore.data);
}, 500);
</script>
