<template>
  <div v-if="scan" class="flex flex-col gap-2">
    <div class="flex items-center justify-between gap-2 text-xs">
      <span class="font-semibold">LiDAR in base_link</span>
      <span class="text-surface-500 dark:text-surface-400">
        {{ validPointCount }} points · {{ displayRange.toFixed(1) }} m radius
      </span>
    </div>
    <canvas
      ref="canvas"
      class="aspect-square max-h-[420px] w-full rounded-lg border border-surface-200 bg-surface-950 dark:border-surface-700"
      aria-label="Polar LiDAR scan preview with forward safety zones"
    />
    <div class="flex flex-wrap gap-x-4 gap-y-1 text-[0.7rem] text-surface-500">
      <span
        ><i
          class="mr-1 inline-block h-2 w-2 rounded-full bg-cyan-400"
        />return</span
      >
      <span
        ><i class="mr-1 inline-block h-2 w-2 rounded-full bg-red-500" />stop
        zone</span
      >
      <span
        ><i class="mr-1 inline-block h-2 w-2 rounded-full bg-amber-400" />slow
        zone</span
      >
      <span>forward ↑</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useAutonomyStore } from "@/features/autonomy";
import { projectLaserScan } from "@/features/autonomy/lidarPreview";
import { useRobotStore } from "@/features/settings/stores";

const canvas = ref<HTMLCanvasElement | null>(null);
const autonomyStore = useAutonomyStore();
const robotStore = useRobotStore();
let resizeObserver: ResizeObserver | null = null;
let animationFrame: number | null = null;

const scan = computed(() => {
  const envelope = autonomyStore.latest.lidar;
  return envelope?.channel === "lidar" ? envelope.payload : null;
});

const transform = computed(
  () => robotStore.data.localization_sensors.lidar.transform,
);
const safety = computed(() => robotStore.data.lidar_safety);
const points = computed(() =>
  scan.value ? projectLaserScan(scan.value, transform.value) : [],
);
const validPointCount = computed(() => points.value.length);
const displayRange = computed(() => {
  const scanRange = scan.value?.range_max_m ?? 5;
  const safetyRange = safety.value.slow_distance_m ?? 0;
  return Math.max(0.5, Math.min(scanRange, Math.max(5, safetyRange * 1.25)));
});

const scheduleDraw = () => {
  if (animationFrame !== null) cancelAnimationFrame(animationFrame);
  animationFrame = requestAnimationFrame(draw);
};

const polarCanvasPoint = (
  center: number,
  scale: number,
  distance: number,
  angle: number,
) => ({
  x: center - Math.sin(angle) * distance * scale,
  y: center - Math.cos(angle) * distance * scale,
});

const drawSafetySector = (
  context: CanvasRenderingContext2D,
  center: number,
  scale: number,
) => {
  if (!safety.value.enabled) return;
  const halfAngle = (safety.value.front_half_angle_deg * Math.PI) / 180;
  const stopDistance = safety.value.stop_distance_m;
  const slowDistance = safety.value.slow_distance_m;
  if (stopDistance === null || slowDistance === null) return;

  const drawSector = (distance: number, color: string) => {
    const start = polarCanvasPoint(center, scale, distance, halfAngle);
    context.beginPath();
    context.moveTo(center, center);
    context.lineTo(start.x, start.y);
    context.arc(
      center,
      center,
      distance * scale,
      -Math.PI / 2 - halfAngle,
      -Math.PI / 2 + halfAngle,
    );
    context.closePath();
    context.fillStyle = color;
    context.fill();
  };

  drawSector(slowDistance, "rgba(251, 191, 36, 0.16)");
  drawSector(stopDistance, "rgba(239, 68, 68, 0.28)");
};

const draw = () => {
  animationFrame = null;
  const element = canvas.value;
  if (!element || !scan.value) return;
  const bounds = element.getBoundingClientRect();
  const size = Math.max(
    1,
    Math.floor(Math.min(bounds.width, bounds.height || bounds.width)),
  );
  const pixelRatio = window.devicePixelRatio || 1;
  const targetSize = Math.floor(size * pixelRatio);
  if (element.width !== targetSize || element.height !== targetSize) {
    element.width = targetSize;
    element.height = targetSize;
  }
  const context = element.getContext("2d");
  if (!context) return;
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.clearRect(0, 0, size, size);
  const center = size / 2;
  const scale = (size * 0.46) / displayRange.value;

  context.strokeStyle = "rgba(148, 163, 184, 0.25)";
  context.lineWidth = 1;
  for (const ratio of [0.25, 0.5, 0.75, 1]) {
    context.beginPath();
    context.arc(
      center,
      center,
      displayRange.value * ratio * scale,
      0,
      Math.PI * 2,
    );
    context.stroke();
  }
  context.beginPath();
  context.moveTo(center, size * 0.04);
  context.lineTo(center, size * 0.96);
  context.moveTo(size * 0.04, center);
  context.lineTo(size * 0.96, center);
  context.stroke();

  drawSafetySector(context, center, scale);

  context.fillStyle = "rgb(34, 211, 238)";
  for (const point of points.value) {
    if (point.distance_m > displayRange.value) continue;
    const x = center - point.y_m * scale;
    const y = center - point.x_m * scale;
    context.beginPath();
    context.arc(x, y, 1.7, 0, Math.PI * 2);
    context.fill();
  }

  context.fillStyle = "rgb(226, 232, 240)";
  context.fillRect(center - 4, center - 7, 8, 14);
  context.beginPath();
  context.moveTo(center, center - 12);
  context.lineTo(center - 5, center - 5);
  context.lineTo(center + 5, center - 5);
  context.closePath();
  context.fill();
};

watch(
  [() => scan.value?.header.sequence, transform, safety, displayRange],
  () => void nextTick(scheduleDraw),
  { deep: true },
);

onMounted(() => {
  if (canvas.value) {
    resizeObserver = new ResizeObserver(scheduleDraw);
    resizeObserver.observe(canvas.value);
  }
  scheduleDraw();
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  if (animationFrame !== null) cancelAnimationFrame(animationFrame);
});
</script>
