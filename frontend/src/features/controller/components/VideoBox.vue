<template>
  <div class="video-box-container">
    <div class="controls">
      <div class="field">
        <ToggleSwitch
          v-tooltip="'Toggle Fullscreen'"
          id="fullscreen"
          class="fullscreen-switch"
          v-model="fullScreen"
        />
      </div>
    </div>

    <div
      class="video-box"
      ref="videoBox"
      :style="{ width: width + 'px', height: height + 'px' }"
    >
      <img :src="imgPath" class="image-feed" alt="Video" />
      <div class="resizers" @mousedown="initResize">
        <div class="resizer top-left" data-resize="top-left"></div>
        <div class="resizer top-right" data-resize="top-right"></div>
        <div class="resizer bottom-left" data-resize="bottom-left"></div>
        <div class="resizer bottom-right" data-resize="bottom-right"></div>
        <div class="resizer top" data-resize="top"></div>
        <div class="resizer right" data-resize="right"></div>
        <div class="resizer bottom" data-resize="bottom"></div>
        <div class="resizer left" data-resize="left"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import ToggleSwitch from "primevue/toggleswitch";

const imgPath = "/mjpg";
const fullScreen = ref(false);

const windowInnerHeight = ref(window.innerHeight);
const windowInnerWidth = ref(window.innerWidth);

const width = ref(1280);
const height = ref(720);

const videoBox = ref<HTMLDivElement | null>(null);

const setFullWidthHeight = () => {
  width.value = windowInnerWidth.value;
  height.value = windowInnerHeight.value;
};

const resetSize = () => {
  width.value = 1280;
  height.value = 720;
};

watch(
  () => fullScreen.value,
  (newVal) => {
    if (newVal) {
      setFullWidthHeight();
    } else {
      resetSize();
    }
  },
);

const handleResize = () => {
  windowInnerHeight.value = window.innerHeight;
  windowInnerWidth.value = window.innerWidth;

  if (fullScreen.value) {
    setFullWidthHeight();
  }
};

const resizing = ref(false);
const resizeType = ref("");
const startX = ref(0);
const startY = ref(0);
const startWidth = ref(0);
const startHeight = ref(0);

const initResize = (event: MouseEvent) => {
  if (!(event.target as HTMLElement).classList.contains("resizer")) return;
  resizing.value = true;
  resizeType.value = (event.target as HTMLElement).dataset.resize || "";
  startX.value = event.clientX;
  startY.value = event.clientY;
  startWidth.value = width.value;
  startHeight.value = height.value;

  window.addEventListener("mouseup", stopResize);
  window.addEventListener("mousemove", doResize);
};

const doResize = (event: MouseEvent) => {
  if (!resizing.value) return;
  if (resizeType.value.includes("right")) {
    width.value = startWidth.value + (event.clientX - startX.value);
  } else if (resizeType.value.includes("left")) {
    width.value = startWidth.value - (event.clientX - startX.value);
  }
  if (resizeType.value.includes("bottom")) {
    height.value = startHeight.value + (event.clientY - startY.value);
  } else if (resizeType.value.includes("top")) {
    height.value = startHeight.value - (event.clientY - startY.value);
  }
};

const stopResize = () => {
  if (!resizing.value) return;
  resizing.value = false;
  window.removeEventListener("mousemove", doResize);
  window.removeEventListener("mouseup", stopResize);
};

onMounted(() => {
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
});
</script>

<style scoped lang="scss">
.video-box-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  height: 100vh;
  color: var(--p-primary-200);
}

.field {
  display: flex;

  align-items: center;
  samp {
    font-weight: bold;
  }
}

.controls {
  position: absolute;
  padding: 10px;
  right: 0;
  top: 0;
  z-index: 12;
  margin-bottom: 1rem;
}

.controls label {
  padding: 0 0.5rem 0 0;
}

.video-box {
  position: relative;

  display: flex;
  align-items: center;
  justify-content: center;

  box-sizing: border-box;
  user-select: none;
}

.image-feed {
  width: 100%;
  display: block;
  height: 100%;
  user-select: none;
}

.resizers {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  pointer-events: none;
  z-index: 10;
  overflow: hidden;
}

.resizer {
  position: absolute;
  pointer-events: all;
  opacity: 0.1;
}

$base-size: 120px;

.resizer.top-left,
.resizer.top-right,
.resizer.bottom-left,
.resizer.bottom-right {
  width: $base-size;
  height: $base-size;
  z-index: 11;
  border-radius: 50%;
  background-color: var(--vt-c-divider-dark-1);
}

.resizer.top-left {
  top: calc(-#{$base-size} / 2);
  left: calc(-#{$base-size} / 2);
  cursor: nwse-resize;
}

.resizer.top-right {
  top: calc(-#{$base-size} / 2);
  right: calc(-#{$base-size} / 2);
  cursor: nesw-resize;
}

.resizer.bottom-left {
  bottom: calc(-#{$base-size} / 2);
  left: calc(-#{$base-size} / 2);
  cursor: nesw-resize;
}

.resizer.bottom-right {
  bottom: calc(-#{$base-size} / 2);
  right: calc(-#{$base-size} / 2);

  cursor: nwse-resize;
}

.resizer.top,
.resizer.bottom {
  left: 50%;
  width: 100%;
  height: 50%;
  cursor: ns-resize;
  margin-left: -50%;
}

.resizer.top {
  top: -5px;
}

.resizer.bottom {
  bottom: -5px;
}

.resizer.left,
.resizer.right {
  width: 20px;
  height: 100%;
  cursor: ew-resize;
}

.resizer.left {
  left: -5px;
}

.resizer.right {
  right: -5px;
}
</style>
