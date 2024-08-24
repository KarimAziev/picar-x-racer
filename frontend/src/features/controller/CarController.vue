<template>
  <div class="wrapper">
    <div class="content">
      <VideoBox />
    </div>
    <div class="right" v-if="loaded">
      <Controller />
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import { useSettingsStore } from "@/features/settings/stores";

const storeSettings = useSettingsStore();
const loaded = computed(() => storeSettings.loaded);

const VideoBox = defineAsyncComponent({
  loader: () => import("@/features/controller/components/VideoBox.vue"),
});

const Controller = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Controller.vue"),
});
</script>

<style scoped lang="scss">
.wrapper {
  width: 100%;
  display: flex;
}

.content {
  flex: auto;
}
.right {
  position: absolute;
  right: 0;
  width: 400px;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 1rem 0;
  justify-content: space-between;
  align-items: center;
}
</style>
