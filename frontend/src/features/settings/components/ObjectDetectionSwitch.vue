<template>
  <div :class="class" class="field">
    <ToggleSwitch
      @update:model-value="
        (newVal) =>
          camStore.updateCameraParams({
            video_feed_object_detection: newVal,
          })
      "
      :pt="{ input: { id: 'video_feed_object_detection' } }"
      v-model="camStore.data.video_feed_object_detection"
    />
    <span v-if="label">{{ label }}</span>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { watch } from "vue";

import { useSettingsStore, useCameraStore } from "@/features/settings/stores";
import ToggleSwitch from "primevue/toggleswitch";

defineProps<{ class?: string; label?: string }>();

const store = useSettingsStore();
const camStore = useCameraStore();

watch(
  () => store.settings.video_feed_object_detection,
  (newVal) => {
    camStore.updateCameraParams({
      video_feed_object_detection: newVal,
    });
  },
);
</script>
<style scoped lang="scss">
.field {
  display: flex;
  gap: 10px;
  margin: 10px 0;
  align-items: center;
}
</style>
