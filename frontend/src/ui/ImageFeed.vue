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
import { computed, watch } from "vue";

const settingsStore = useSettingsStore();
const videoFeedUrl = computed(() => settingsStore.settings.video_feed_url);
const handleOnLoad = () => {
  console.log("LOADED");
};

watch(() => videoFeedUrl.value, settingsStore.fetchDimensions);
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
