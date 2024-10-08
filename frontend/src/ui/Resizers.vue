<template>
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
</template>

<script setup lang="ts">
import { ref } from "vue";

const resizing = ref(false);
const resizeType = ref("");
const startX = ref(0);
const startY = ref(0);
const startWidth = ref(0);
const startHeight = ref(0);
const size = defineModel<{ width: number; height: number }>();

const initResize = (event: MouseEvent) => {
  if (!size.value) {
    return;
  }
  if (event.button !== 0) {
    return;
  }
  if (!(event.target as HTMLElement).classList.contains("resizer")) {
    return;
  }
  resizing.value = true;
  resizeType.value = (event.target as HTMLElement).dataset.resize || "";
  startX.value = event.clientX;
  startY.value = event.clientY;
  if (size.value) {
    startWidth.value = size.value?.width;
    startHeight.value = size.value?.height;
  }

  window.addEventListener("mouseup", stopResize);
  window.addEventListener("mousemove", doResize);
};

const doResize = (event: MouseEvent) => {
  if (!size.value) {
    return;
  }
  if (!resizing.value) {
    return;
  }
  if (resizeType.value.includes("right")) {
    size.value.width = startWidth.value + (event.clientX - startX.value);
  } else if (resizeType.value.includes("left")) {
    size.value.width = startWidth.value - (event.clientX - startX.value);
  }
  if (resizeType.value.includes("bottom")) {
    size.value.height = startHeight.value + (event.clientY - startY.value);
  } else if (resizeType.value.includes("top")) {
    size.value.height = startHeight.value - (event.clientY - startY.value);
  }
};

const stopResize = () => {
  if (!resizing.value) {
    return;
  }
  resizing.value = false;
  window.removeEventListener("mousemove", doResize);
  window.removeEventListener("mouseup", stopResize);
};
</script>

<style scoped lang="scss">
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
  &:hover {
    background-color: var(--robo-color-primary);
  }
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
  height: 10%;
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
