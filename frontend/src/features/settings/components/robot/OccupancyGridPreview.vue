<template>
  <div v-if="mappingEnabled" class="flex flex-col gap-2">
    <div class="flex items-center justify-between gap-2 text-xs">
      <span class="font-semibold">Local occupancy map</span>
      <span v-if="map" class="text-surface-500 dark:text-surface-400">
        {{ map.width }}×{{ map.height }} · {{ map.resolution_m }} m/cell
      </span>
    </div>
    <div v-if="store.mapError" class="text-xs text-red-500">
      {{ store.mapError }}
    </div>
    <div
      v-else-if="!map"
      class="rounded-lg border border-dashed border-surface-300 p-4 text-center text-xs text-surface-500 dark:border-surface-700"
    >
      {{ emptyMapMessage }}
    </div>
    <canvas
      v-else
      ref="canvas"
      class="max-h-[420px] w-full rounded-lg border border-surface-200 bg-surface-900 [image-rendering:pixelated] dark:border-surface-700"
      aria-label="Local occupancy grid in the odom frame"
    />
    <div v-if="map" class="flex gap-4 text-[0.7rem] text-surface-500">
      <span><i class="mr-1 inline-block h-2 w-2 bg-slate-700" />unknown</span>
      <span><i class="mr-1 inline-block h-2 w-2 bg-slate-100" />free</span>
      <span><i class="mr-1 inline-block h-2 w-2 bg-red-500" />occupied</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useAutonomyStore } from "@/features/autonomy";
import { useRobotStore } from "@/features/settings/stores";

const canvas = ref<HTMLCanvasElement | null>(null);
const store = useAutonomyStore();
const robotStore = useRobotStore();
let pollTimer: ReturnType<typeof setInterval> | null = null;
let resizeObserver: ResizeObserver | null = null;
let animationFrame: number | null = null;

const mappingEnabled = computed(() => robotStore.data.local_mapping.enabled);
const map = computed(() => store.localMap);
const emptyMapMessage = computed(() => {
  if (store.mappingSession?.state === "idle") {
    return "Mapping session is idle. Start it from the autonomy workspace when ready.";
  }
  if (store.mappingSession?.state === "paused") {
    return "Mapping session is paused. The existing map is being retained.";
  }
  return "Waiting for synchronized LiDAR and odometry…";
});

const scheduleDraw = () => {
  if (animationFrame !== null) cancelAnimationFrame(animationFrame);
  animationFrame = requestAnimationFrame(draw);
};

const draw = () => {
  animationFrame = null;
  const element = canvas.value;
  const grid = map.value;
  if (!element || !grid) return;
  const bounds = element.getBoundingClientRect();
  const cssWidth = Math.max(1, Math.floor(bounds.width));
  const cssHeight = Math.max(
    1,
    Math.floor((cssWidth * grid.height) / grid.width),
  );
  const pixelRatio = window.devicePixelRatio || 1;
  element.style.height = `${cssHeight}px`;
  element.width = Math.floor(cssWidth * pixelRatio);
  element.height = Math.floor(cssHeight * pixelRatio);
  const context = element.getContext("2d");
  if (!context) return;

  const bitmap = document.createElement("canvas");
  bitmap.width = grid.width;
  bitmap.height = grid.height;
  const bitmapContext = bitmap.getContext("2d");
  if (!bitmapContext) return;
  const image = bitmapContext.createImageData(grid.width, grid.height);
  for (let y = 0; y < grid.height; y += 1) {
    for (let x = 0; x < grid.width; x += 1) {
      const value = grid.data[y * grid.width + x];
      const targetY = grid.height - y - 1;
      const offset = (targetY * grid.width + x) * 4;
      if (value < 0) {
        image.data.set([51, 65, 85, 255], offset);
      } else if (value >= 65) {
        image.data.set([239, 68, 68, 255], offset);
      } else {
        const shade = Math.round(241 - (value / 100) * 140);
        image.data.set([shade, shade, shade, 255], offset);
      }
    }
  }
  bitmapContext.putImageData(image, 0, 0);
  context.imageSmoothingEnabled = false;
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.clearRect(0, 0, cssWidth, cssHeight);
  context.drawImage(bitmap, 0, 0, cssWidth, cssHeight);
};

const stopPolling = () => {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
};

watch(
  mappingEnabled,
  (enabled) => {
    stopPolling();
    if (!enabled) return;
    void store.refreshLocalMap();
    pollTimer = setInterval(() => void store.refreshLocalMap(), 1000);
  },
  { immediate: true },
);

watch(
  () => map.value?.header.sequence,
  () => void nextTick(scheduleDraw),
);

watch(canvas, (element, previous) => {
  if (previous) resizeObserver?.unobserve(previous);
  if (element) {
    resizeObserver?.observe(element);
    scheduleDraw();
  }
});

onMounted(() => {
  resizeObserver = new ResizeObserver(scheduleDraw);
  if (canvas.value) resizeObserver.observe(canvas.value);
  scheduleDraw();
});

onUnmounted(() => {
  stopPolling();
  resizeObserver?.disconnect();
  if (animationFrame !== null) cancelAnimationFrame(animationFrame);
});
</script>
