<template>
  <ScanLines v-if="!loaded" class="box" />
  <img
    v-else
    :src="videoFeedUrl"
    class="image-feed"
    alt="Video"
    @load="handleOnLoad"
  />
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import { computed } from "vue";
import ScanLines from "@/ui/ScanLines.vue";

const settingsStore = useSettingsStore();
const loaded = computed(() => settingsStore.loaded);

const videoFeedUrl = "/mjpg";

const handleOnLoad = async () => {};
</script>

<style scoped lang="scss">
.image-feed {
  width: 100%;
  display: block;
  height: 100%;
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);
  user-select: none;
}
.box {
  opacity: 1;
  width: 100%;
  height: 100%;
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);
  user-select: none;
}
</style>
