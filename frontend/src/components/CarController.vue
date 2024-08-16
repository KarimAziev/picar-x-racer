<template>
  <div class="wrapper">
    <div class="content">
      <VideoBox />
    </div>
    <div class="right">
      <CarModelViewer />
      <TextInfo />
      <Speedometer />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useControllerStore } from "@/stores/controller";
import Speedometer from "@/components/Speedometer.vue";
import TextInfo from "@/components/TextInfo.vue";
import VideoBox from "@/components/VideoBox.vue";
import CarModelViewer from "@/components/CarModelViewer/CarModelViewer.vue";

const store = useControllerStore();
const loopTimer = ref();
const activeKeys = ref(new Set<string>());
const inactiveKeys = ref(new Set<string>());

const handleKeyUp = (event: KeyboardEvent) => {
  const key = event.key;
  activeKeys.value.delete(key);
};

const handleKeyDown = (event: KeyboardEvent) => {
  const key = event.key;
  if (!event.repeat) {
    activeKeys.value.add(key);
  }

  const otherMethods: { [key: string]: Function } = {
    t: store.takePhoto,
    m: store.playMusic,
    r: store.playSound,
    k: store.sayText,
    "=": store.increaseMaxSpeed,
    "-": store.decreaseMaxSpeed,
    ArrowRight: store.increaseCamPan,
    ArrowLeft: store.decreaseCamPan,
    ArrowUp: store.increaseCamTilt,
    ArrowDown: store.decreaseCamTilt,
    "0": store.resetCameraRotate,
  };

  if (otherMethods[key]) {
    event.preventDefault();
    otherMethods[key]();
  }
};

const gameLoop = () => {
  updateCarState();
  loopTimer.value = setTimeout(() => gameLoop(), 50);
};

const updateCarState = () => {
  if (activeKeys.value.has("w")) {
    store.accelerate();
  } else if (activeKeys.value.has("s")) {
    store.decelerate();
  } else {
    store.slowdown();
  }

  if (activeKeys.value.has("a")) {
    inactiveKeys.value.add("a");
    store.setDirServoAngle(-30);
  } else if (activeKeys.value.has("d")) {
    inactiveKeys.value.add("d");
    store.setDirServoAngle(30);
  } else if (inactiveKeys.value.has("d") || inactiveKeys.value.has("a")) {
    inactiveKeys.value.delete("d");
    inactiveKeys.value.delete("a");
    store.resetDirServoAngle();
  }

  if (activeKeys.value.has(" ")) {
    store.stop();
  }
};

onMounted(() => {
  store.reconnectedEnabled = true;
  store.initializeWebSocket("ws://" + window.location.hostname + ":8765");
  window.addEventListener("keydown", handleKeyDown);
  window.addEventListener("keyup", handleKeyUp);
  gameLoop();
});

onUnmounted(() => {
  if (loopTimer.value) {
    clearTimeout(loopTimer.value);
    loopTimer.value = undefined;
  }
  window.removeEventListener("keydown", handleKeyDown);
  window.removeEventListener("keyup", handleKeyUp);
  store.cleanup();
});
</script>

<style scoped lang="scss">
@import "/src/assets/scss/variables.scss";

.wrapper {
  width: 100%;
  display: flex;
}
.side-menu {
  position: relative;
}
.content {
  flex: auto;
}
.video-box {
  width: 100%;
  height: 100vh;
  text-align: center;
  justify-items: center;
  justify-content: center;
  display: flex;
  align-items: center;
  font-weight: bold;
  font-size: 20px;
  background: var(--video-bg-color);
}

.video-box > img {
  min-width: 1280px;
  min-height: 720px;
  max-height: 100vh;
}

.right {
  position: absolute;
  right: 0;
  width: 400px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.right {
  position: absolute;
  top: 0;
  right: 0;
  width: 400px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}
</style>
