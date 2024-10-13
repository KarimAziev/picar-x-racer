<template>
  <div class="wrapper">
    <div ref="joystickZone" class="joystick-zone" v-if="isMobile"></div>
    <div ref="joystickCam" class="joystick-camera" v-if="isMobile"></div>
    <div class="content"><VideoBox /></div>

    <GaugesBlock class="gauges" v-if="!isMobile">
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
import { useJoystickControl } from "@/features/controller/useJoysticManager";
import { isMobileDevice } from "@/util/device";

const settingsStore = useSettingsStore();
const isMobile = computed(() => isMobileDevice());
const controllerStore = useControllerStore();
const popupStore = usePopupStore();

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

const { joystickZone } = useJoystickControl(controllerStore);
const { joystickZone: joystickCam } = useJoystickControl(controllerStore, {
  position: { right: "20%", top: "50%" },
});
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

.joystick-zone,
.joystick-camera {
  position: fixed;
  width: 50%;
  bottom: 0;
  height: 90%;
}

.joystick-zone {
  left: 0;
  z-index: 30;
}

.joystick-camera {
  left: 50%;
  z-index: 30;
}

.joystick-zone.active,
.joystick-camera.active {
  display: block;
}

.joystick-zone > h1,
.joystick-camera > h1 {
  position: absolute;
  padding: 10px 10px;
  margin: 0;
  color: white;
  right: 0;
  bottom: 0;
}

.joystick-zone.dynamic {
  background: rgba(0, 0, 255, 0.1);
}

.joystick-zone.semi {
  background: rgba(255, 255, 255, 0.1);
}

.joystick-zone.static {
  background: var(--robo-color-text);
}

.joystick-camera.dynamic {
  background: rgba(0, 0, 255, 0.1);
}

.joystick-camera.semi {
  background: rgba(255, 255, 255, 0.1);
}

.joystick-camera.static {
  background: rgba(255, 0, 0, 0.1);
}
</style>
