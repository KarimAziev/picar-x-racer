<template>
  <div
    class="absolute inset-0 pointer-events-none z-10 overflow-hidden"
    @mousedown="initResize"
  >
    <!-- Top-Left Resizer -->
    <div
      class="z-11 absolute w-[120px] h-[120px] rounded-full opacity-10 pointer-events-auto hover:bg-primary-500 cursor-nwse-resize -top-[60px] -left-[60px]"
      data-resize="top-left"
    ></div>

    <!-- Top-Right Resizer -->
    <div
      class="z-11 absolute w-[120px] h-[120px] rounded-full opacity-10 pointer-events-auto hover:bg-primary-500 cursor-nesw-resize -top-[60px] -right-[60px]"
      data-resize="top-right"
    ></div>

    <!-- Bottom-Left Resizer -->
    <div
      class="z-11 absolute w-[120px] h-[120px] rounded-full opacity-10 pointer-events-auto hover:bg-primary-500 cursor-nesw-resize -bottom-[60px] -left-[60px]"
      data-resize="bottom-left"
    ></div>

    <!-- Bottom-Right Resizer -->
    <div
      class="z-11 absolute w-[120px] h-[120px] rounded-full opacity-10 pointer-events-auto hover:bg-primary-500 cursor-nwse-resize -bottom-[60px] -right-[60px]"
      data-resize="bottom-right"
    ></div>

    <!-- Middle Top Resizer -->
    <div
      class="absolute left-1/2 transform -translate-x-1/2 w-full h-[10%] opacity-10 pointer-events-auto cursor-ns-resize -top-[5px]"
      data-resize="top"
    ></div>

    <!-- Middle Bottom Resizer -->
    <div
      class="absolute left-1/2 transform -translate-x-1/2 w-full h-[10%] opacity-10 pointer-events-auto cursor-ns-resize -bottom-[5px]"
      data-resize="bottom"
    ></div>

    <!-- Middle Left Resizer -->
    <div
      class="absolute top-0 w-[20px] h-full opacity-10 pointer-events-auto cursor-ew-resize -left-[5px]"
      data-resize="left"
    ></div>

    <!-- Middle Right Resizer -->
    <div
      class="absolute top-0 w-[20px] h-full opacity-10 pointer-events-auto cursor-ew-resize -right-[5px]"
      data-resize="right"
    ></div>
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
  if (!(event.target as HTMLElement)?.hasAttribute("data-resize")) {
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
