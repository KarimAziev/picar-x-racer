<template>
  <div ref="joystickZoneY" class="joystick-zone-left"></div>
  <div ref="joystickZoneX" class="joystick-zone-right"></div>
</template>
<script setup lang="ts">
import { ref } from "vue";
import { useControllerStore } from "@/features/controller/store";
import { useJoystickControl } from "@/features/joystick/composables/useJoysticManager";

const controllerStore = useControllerStore();
const timeout = ref<NodeJS.Timeout>();

const { joystickZone: joystickZoneY, params } = useJoystickControl(
  controllerStore,
  {
    position: { left: "15%", bottom: "100px" },
  },
  {
    onEnd: () => {
      controllerStore.stop();
      controllerStore.resetDirServoAngle();
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
  {
    position: { bottom: "100px", right: "15%" },
    lockX: true,
  },
  {
    onStart: handleOnStart,
    onEnd: handleEnd,
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
