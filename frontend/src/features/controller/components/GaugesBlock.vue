<template>
  <div class="gauges-block" :class="class">
    <ToggleableView setting="text_info_view">
      <TextInfo />
    </ToggleableView>
    <slot></slot>
    <ToggleableView setting="speedometer_view" v-if="!isMobile">
      <Speedometer />
    </ToggleableView>
  </div>
</template>
<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import ToggleableView from "@/ui/ToggleableView.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";

const isMobile = useDeviceWatcher();

defineProps<{ class?: string }>();

const TextInfo = defineAsyncComponent({
  loader: () => import("@/features/controller/components/TextInfo.vue"),
});

const Speedometer = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Speedometer.vue"),
});
</script>

<style scoped lang="scss">
.gauges-block {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: end;
  right: 0;
  bottom: 0;
  width: 300px;

  @media (min-width: 1200px) {
    width: 400px;
  }

  @media screen and (max-width: 992px) and (orientation: portrait) {
    top: 5%;
    width: 100%;
    left: 5%;
    align-items: flex-start;
  }

  @media screen and (max-width: 992px) and (orientation: landscape) {
    top: 10%;
    width: 100%;
    align-items: flex-start;
  }
}
</style>
