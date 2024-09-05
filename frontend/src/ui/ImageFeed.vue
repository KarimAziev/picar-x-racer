<template>
  <img
    :src="videoFeedUrl"
    class="image-feed"
    alt="Video"
    @load="handleOnLoad"
  />
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import { computed, onUnmounted } from "vue";
import { cameraClose } from "@/features/controller/api";

const settingsStore = useSettingsStore();
const videoFeedUrl = computed(() => settingsStore.settings.video_feed_url);

const handleOnLoad = async () => {
  await settingsStore.fetchDimensions();
};
onUnmounted(async () => {
  try {
    await cameraClose();
  } catch (error) {
    console.error(error);
  }
});
</script>

<style scoped lang="scss">
.image-feed {
  width: 100%;
  display: block;
  height: 100%;
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);
  user-select: none;
}
</style>
