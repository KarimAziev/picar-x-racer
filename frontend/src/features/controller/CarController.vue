<template>
  <div class="wrapper">
    <div class="content" v-if="!isSettingsOpened"><VideoBox /></div>

    <GaugesBlock class="gauges">
      <ToggleableView setting="car_model_view">
        <CarModelViewer
          class="car-model"
          :zoom="4"
          :rotationY="20"
          :rotationX="0"
        />
      </ToggleableView>
    </GaugesBlock>
  </div>
</template>
<script setup lang="ts">
import { computed, defineAsyncComponent } from "vue";
import { usePopupStore } from "@/features/settings/stores";
import { useCarController } from "@/features/controller/composable";
import { useSettingsStore } from "@/features/settings/stores";
import { useControllerStore } from "@/features/controller/store";
import ToggleableView from "@/ui/ToggleableView.vue";
import GaugesBlock from "@/features/controller/components/GaugesBlock.vue";

const settingsStore = useSettingsStore();
const controllerStore = useControllerStore();
const popupStore = usePopupStore();
const isSettingsOpened = computed(() => popupStore.isOpen);

const CarModelViewer = defineAsyncComponent({
  loader: () =>
    import(
      "@/features/controller/components/CarModelViewer/CarModelViewer.vue"
    ),
});

const VideoBox = defineAsyncComponent({
  loader: () => import("@/features/controller/components/VideoBox.vue"),
});

useCarController(controllerStore, settingsStore, popupStore);
</script>

<style scoped lang="scss">
.wrapper {
  width: 100%;
  display: flex;
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
