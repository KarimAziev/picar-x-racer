<template>
  <div class="gauges-block" :class="class">
    <ToggleableView setting="text_info_view">
      <TextInfo />
      <TextToSpeechInput v-if="isMobile" />
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
import TextToSpeechInput from "@/features/settings/components/TextToSpeechInput.vue";

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
  width: fit-content;

  @media (min-width: 1200px) {
    width: fit-content;
    bottom: 0;
    right: 0;
  }

  @media screen and (max-width: 992px) and (orientation: portrait) {
    top: 5%;
    width: 50%;
    left: 5%;
    align-items: flex-start;
  }

  @media screen and (max-width: 480px) and (orientation: portrait) {
    top: 5%;
    width: unset;
    left: 5%;
    align-items: flex-start;
  }

  @media screen and (max-width: 992px) and (orientation: landscape) {
    top: 10%;
    width: fit-content;
    align-items: flex-start;
  }

}
</style>
