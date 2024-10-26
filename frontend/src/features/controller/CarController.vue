<template>
  <div class="wrapper">
    <JoysticZone v-if="isMobile" />
    <div class="content">
      <VideoBox />

      <GaugesBlock class="gauges">
        <ToggleableView setting="car_model_view" v-if="!isMobile">
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
import { usePopupStore } from "@/features/settings/stores";
import { useCarController } from "@/features/controller/composable";
import { useSettingsStore } from "@/features/settings/stores";
import { useControllerStore } from "@/features/controller/store";
import ToggleableView from "@/ui/ToggleableView.vue";
import GaugesBlock from "@/features/controller/components/GaugesBlock.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";

const settingsStore = useSettingsStore();
const isMobile = useDeviceWatcher();
const controllerStore = useControllerStore();
const popupStore = usePopupStore();

const CarModelViewer = defineAsyncComponent({
  loader: () =>
    import(
      "@/features/controller/components/CarModelViewer/CarModelViewer.vue"
    ),
});

const JoysticZone = defineAsyncComponent({
  loader: () => import("@/features/controller/components/JoysticZone.vue"),
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
