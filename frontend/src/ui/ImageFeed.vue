<template>
  <ScanLines v-if="cameraStore.loading" />
  <img
    v-else
    :src="videoFeedUrl"
    class="image-feed"
    alt="Video"
    @load="handleOnLoad"
  />
</template>

<script setup lang="ts">
import { useSettingsStore, useCameraStore } from "@/features/settings/stores";
import { computed, onUnmounted, onMounted } from "vue";
import ScanLines from "@/ui/ScanLines.vue";

const settingsStore = useSettingsStore();
const cameraStore = useCameraStore();
const videoFeedUrl = computed(() => settingsStore.settings.video_feed_url);

const handleOnLoad = async () => {
  await settingsStore.fetchDimensions();
};

onUnmounted(cameraStore.cameraClose);
onMounted(cameraStore.cameraStart);
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
