<template>
  <VideoBox />
  <GaugesBlock class="gauges">
    <ToggleableView setting="general.robot_3d_view" v-if="!isMobile">
      <CarModelViewer
        class="portrait:display-hidden absolute -top-[90%]"
        :zoom="4"
        :rotationY="20"
        :rotationX="0"
      />
    </ToggleableView>
  </GaugesBlock>
</template>
<script setup lang="ts">
import { defineAsyncComponent, inject } from "vue";
import GaugesBlock from "@/features/controller/components/GaugesBlock.vue";
import ToggleableView from "@/ui/ToggleableView.vue";
import type { Ref } from "vue";

const isMobile = inject<Ref<boolean, boolean>>("isMobile");

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
