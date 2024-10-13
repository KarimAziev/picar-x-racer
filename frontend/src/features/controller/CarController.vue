<template>
  <div class="wrapper">
    <div ref="joystickZoneY" class="joystick-zone-left" v-if="isMobile"></div>
    <div ref="joystickZoneX" class="joystick-zone-right" v-if="isMobile"></div>
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
import { useJoystickCameraControl } from "@/features/controller/useJoysticCameraController";
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

const { joystickZone: joystickZoneY } = useJoystickControl(controllerStore, {
  lockY: true,
  position: { left: "15%", bottom: "55px" },
});
const { joystickZone: joystickZoneX } = useJoystickControl(controllerStore, {
  position: { right: "15%", bottom: "55px" },
  lockX: true,
});
const { joystickZone: joystickCam } = useJoystickCameraControl(
  controllerStore,
  {
    position: { right: "50%", bottom: "55px" },
    restOpacity: 0.1,
  },
);
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

.joystick-zone-left,
.joystick-zone-right {
  bottom: 0;
}

.joystick-camera {
  height: 50%;
}

.joystick-zone-left {
  left: 0;
  z-index: 30;
}

.joystick-zone-right {
  left: 50%;
  z-index: 30;
}

.joystick-zone-left.active,
.joystick-zone-right.active {
  display: block;
}

.joystick-zone-left > h1,
.joystick-zone-right > h1 {
  position: absolute;
  padding: 10px 10px;
  margin: 0;
  color: white;
  right: 0;
  bottom: 0;
}

.joystick-camera.static {
  background: rgba(0, 0, 255, 0.1);
}

.joystick-zone-left.dynamic {
  background: rgba(0, 0, 255, 0.1);
}

.joystick-zone-left.semi {
  background: rgba(255, 255, 255, 0.1);
}

.joystick-zone-left.static {
  background: var(--robo-color-text);
}

.joystick-zone-right.dynamic {
  background: rgba(0, 0, 255, 0.1);
}

.joystick-zone-right.semi {
  background: rgba(255, 255, 255, 0.1);
}

.joystick-zone-right.static {
  background: rgba(255, 0, 0, 0.1);
}
</style>
