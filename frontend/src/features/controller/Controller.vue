<template>
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
.car-model {
  position: absolute;
  top: -90%;
}
</style>
