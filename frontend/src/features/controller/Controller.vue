<template>
  <div class="wrapper">
    <div class="content">
      <VideoBox />
      <GaugesBlock class="gauges">
        <ToggleableView setting="general.robot_3d_view" v-if="!isMobile">
          <CarModelViewer
            class="car-model"
            :zoom="4"
            :rotationY="20"
            :rotationX="0"
          />
        </ToggleableView>
      </GaugesBlock>
    </div>
  </div>
</template>
<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import GaugesBlock from "@/features/controller/components/GaugesBlock.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import ToggleableView from "@/ui/ToggleableView.vue";

const isMobile = useDeviceWatcher();

const CarModelViewer = defineAsyncComponent({
  loader: () =>
    import(
      "@/features/controller/components/CarModelViewer/CarModelViewer.vue"
    ),
});

const VideoBox = defineAsyncComponent({
  loader: () => import("@/features/controller/components/VideoBox.vue"),
});
</script>

<style scoped lang="scss">
.wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
}

.content {
  flex: auto;
}

.car-model {
  width: 100%;
  position: fixed;
  top: -5%;
  left: 40%;
}
</style>
