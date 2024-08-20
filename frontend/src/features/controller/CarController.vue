<template>
  <div class="wrapper">
    <div class="content">
      <VideoBox />
    </div>
    <div class="right">
      <Controller />
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted } from "vue";
import VideoBox from "@/features/controller/components/VideoBox.vue";
import { useSettingsStore } from "@/features/settings/stores";
import Controller from "@/features/controller/components/Controller.vue";

const settings = useSettingsStore();

onMounted(() => {
  settings.fetchSettings();
});
</script>

<style scoped lang="scss">
@import "/src/assets/scss/variables.scss";

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
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}
</style>
