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
import ProgressSpinner from "primevue/progressspinner";
import { defineAsyncComponent } from "vue";

const VideoBox = defineAsyncComponent({
  loader: () => import("@/features/controller/components/VideoBox.vue"),
  loadingComponent: ProgressSpinner,
});

const Controller = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Controller.vue"),
  loadingComponent: ProgressSpinner,
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
  justify-content: space-between;
  align-items: center;
}
</style>
