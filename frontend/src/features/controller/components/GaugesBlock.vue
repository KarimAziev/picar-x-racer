<template>
  <div class="gauges-block" :class="class">
    <ToggleableView setting="text_info_view">
      <TextInfo />
    </ToggleableView>
    <slot></slot>
    <ToggleableView setting="speedometer_view">
      <Speedometer />
    </ToggleableView>
  </div>
</template>
<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import ToggleableView from "@/ui/ToggleableView.vue";

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
  width: 400px;
}
</style>
