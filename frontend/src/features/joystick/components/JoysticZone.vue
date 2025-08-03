<template>
  <div ref="joystickZoneY" class="joystick-zone-left"></div>
  <div ref="joystickZoneX" class="joystick-zone-right"></div>
</template>
<script setup lang="ts">
import { ref } from "vue";
import { useControllerStore } from "@/features/controller/store";
import { useJoystickControl } from "@/features/joystick/composables/useJoysticManager";
import { useRobotStore } from "@/features/settings/stores";

const controllerStore = useControllerStore();
const robotStore = useRobotStore();
const timeout = ref<NodeJS.Timeout>();

const sideOffset = "60px";
const bottomOffset = "60px";

const handleStopAll = () => {
  controllerStore.updateCombined({ speed: 0, direction: 0, servoAngle: 0 });
};

const { joystickZone: joystickZoneY, params } = useJoystickControl(
  controllerStore,
  robotStore,
  {
    position: { left: sideOffset, bottom: bottomOffset },
  },
  {
    onEnd: () => {
      handleStopAll();
    },
  },
);

const debounceRecreate = () => {
  if (timeout.value) {
    clearTimeout(timeout.value);
  }
  timeout.value = setTimeout(() => {
    if (params.value) {
      params.value.lockY = false;
    }
  }, 1000);
};

const handleOnStart = () => {
  if (timeout.value) {
    clearTimeout(timeout.value);
  }
  if (params.value) {
    params.value.lockY = true;
  }
};

const handleEnd = () => {
  debounceRecreate();
  controllerStore.resetDirServoAngle();
};

const { joystickZone: joystickZoneX } = useJoystickControl(
  controllerStore,
  robotStore,
  {
    position: { bottom: bottomOffset, right: sideOffset },
    lockX: true,
  },
  {
    onStart: handleOnStart,
    onEnd: handleEnd,
  },
);
</script>
