<template>
  <Button
    class="absolute left-12 top-0 z-12"
    aria-label="Open autonomy workspace"
    icon="pi pi-map"
    severity="secondary"
    text
    rounded
    @click="router.push({ name: 'autonomy' })"
  />
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
import { useRouter } from "vue-router";

const isMobile = inject<Ref<boolean, boolean>>("isMobile");
const router = useRouter();

const CarModelViewer = defineAsyncComponent({
  loader: () =>
    import("@/features/controller/components/CarModelViewer/CarModelViewer.vue"),
});

const VideoBox = defineAsyncComponent({
  loader: () => import("@/features/controller/components/VideoBox.vue"),
});
</script>
