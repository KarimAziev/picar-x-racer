<template>
  <img :src="videoFeedUrl" class="image-feed" alt="Video" />
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import { computed } from "vue";

const settingsStore = useSettingsStore();
const videoFeedUrl = computed(() => settingsStore.settings.video_feed_url);
</script>

<style scoped lang="scss">
.image-feed {
  width: 100%;
  display: block;
  height: 100%;

  user-select: none;
}
</style>
