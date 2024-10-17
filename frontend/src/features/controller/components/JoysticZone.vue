<template>
  <div ref="joystickZoneY" class="joystick-zone-left"></div>
  <div ref="joystickZoneX" class="joystick-zone-right"></div>
  <div ref="joystickCam" class="joystick-camera"></div>
</template>
<script setup lang="ts">
import { useControllerStore } from "@/features/controller/store";
import { useJoystickControl } from "@/features/controller/useJoysticManager";
import { useJoystickCameraControl } from "@/features/controller/useJoysticCameraController";

const controllerStore = useControllerStore();

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
