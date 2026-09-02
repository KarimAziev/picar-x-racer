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
    <div
      v-if="map"
      class="flex flex-wrap gap-x-4 gap-y-1 text-[0.7rem] text-surface-500"
    >
      <span><i class="mr-1 inline-block h-2 w-2 bg-slate-700" />unknown</span>
      <span><i class="mr-1 inline-block h-2 w-2 bg-slate-100" />free</span>
      <span><i class="mr-1 inline-block h-2 w-2 bg-red-500" />occupied</span>
      <span><i class="mr-1 inline-block h-2 w-2 bg-cyan-400" />odom trail</span>
      <span
        ><i class="mr-1 inline-block h-2 w-2 rounded-full bg-blue-500" />raw
        odometry</span
      >
      <span v-if="localizationEnabled"
        ><i
          class="mr-1 inline-block h-2 w-2 rounded-full border-2 border-emerald-400"
        />fused pose</span
      >
      <span v-if="simulationWorld"
        ><i
          class="mr-1 inline-block h-2 w-2 border border-dashed border-slate-300"
        />known world</span
      >
      <span v-if="simulationWorld"
        ><i
          class="mr-1 inline-block h-2 w-2 rounded-full border border-purple-400"
        />simulated truth</span
      >
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import {
  gridToCanvas,
  useAutonomyStore,
  worldPointToOdom,
  worldToGrid,
  worldToGridUnbounded,
  worldYawToCanvas,
  worldYawToOdom,
  type Point2D,
} from "@/features/autonomy";
import { useRobotStore } from "@/features/settings/stores";

const canvas = ref<HTMLCanvasElement | null>(null);
const store = useAutonomyStore();
const robotStore = useRobotStore();
let pollTimer: ReturnType<typeof setInterval> | null = null;
let resizeObserver: ResizeObserver | null = null;
let animationFrame: number | null = null;
const odometryTrail = ref<Point2D[]>([]);

const mappingEnabled = computed(() => robotStore.data.local_mapping.enabled);
const map = computed(() => store.localMap);
const simulationWorld = computed(() => store.simulation?.world ?? null);
const localizationEnabled = computed(
  () => store.localization?.enabled ?? robotStore.data.pose_estimation.enabled,
);
const odomOriginInWorld = computed(() => {
  const origin = store.simulation?.odom_origin_in_world;
  return origin ? { x: origin.x_m, y: origin.y_m, yaw: origin.yaw_rad } : null;
});
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
  drawKnownWorldOverlay(context, grid, cssWidth, cssHeight);
  drawOdometryOverlay(context, grid, cssWidth, cssHeight);
};

const canvasPoint = (
  grid: NonNullable<typeof map.value>,
  point: Point2D,
  width: number,
  height: number,
) => {
  const gridPoint = worldToGrid(grid, point.x, point.y);
  return gridPoint ? gridToCanvas(grid, gridPoint, width, height) : null;
};

const unboundedCanvasPoint = (
  grid: NonNullable<typeof map.value>,
  point: Point2D,
  width: number,
  height: number,
) =>
  gridToCanvas(
    grid,
    worldToGridUnbounded(grid, point.x, point.y),
    width,
    height,
  );

const drawKnownWorldOverlay = (
  context: CanvasRenderingContext2D,
  grid: NonNullable<typeof map.value>,
  width: number,
  height: number,
) => {
  const world = simulationWorld.value;
  const origin = odomOriginInWorld.value;
  if (!world || !origin) return;
  context.save();
  context.strokeStyle = "#cbd5e1";
  context.lineWidth = 1.25;
  context.globalAlpha = 0.8;
  context.setLineDash([5, 4]);
  context.beginPath();
  for (const segment of world.segments) {
    const start = unboundedCanvasPoint(
      grid,
      worldPointToOdom({ x: segment.start_x_m, y: segment.start_y_m }, origin),
      width,
      height,
    );
    const end = unboundedCanvasPoint(
      grid,
      worldPointToOdom({ x: segment.end_x_m, y: segment.end_y_m }, origin),
      width,
      height,
    );
    context.moveTo(start.x, start.y);
    context.lineTo(end.x, end.y);
  }
  context.stroke();
  context.restore();
};

const drawPoseMarker = (
  context: CanvasRenderingContext2D,
  pose: Point2D,
  yaw: number,
  markerSize: number,
  grid: NonNullable<typeof map.value>,
  options: { fill?: string; stroke: string; lineWidth: number },
) => {
  context.save();
  context.translate(pose.x, pose.y);
  context.rotate(worldYawToCanvas(grid, yaw));
  if (options.fill) context.fillStyle = options.fill;
  context.strokeStyle = options.stroke;
  context.lineWidth = options.lineWidth;
  context.beginPath();
  context.moveTo(markerSize, 0);
  context.lineTo(-markerSize * 0.7, markerSize * 0.65);
  context.lineTo(-markerSize * 0.7, -markerSize * 0.65);
  context.closePath();
  if (options.fill) context.fill();
  context.stroke();
  context.restore();
};

const drawOdometryOverlay = (
  context: CanvasRenderingContext2D,
  grid: NonNullable<typeof map.value>,
  width: number,
  height: number,
) => {
  const visibleTrail = odometryTrail.value
    .map((point) => canvasPoint(grid, point, width, height))
    .filter((point): point is Point2D => point !== null);
  if (visibleTrail.length > 1) {
    context.save();
    context.strokeStyle = "#22d3ee";
    context.lineWidth = 2;
    context.globalAlpha = 0.9;
    context.beginPath();
    context.moveTo(visibleTrail[0].x, visibleTrail[0].y);
    for (const point of visibleTrail.slice(1)) context.lineTo(point.x, point.y);
    context.stroke();
    context.restore();
  }

  const envelope = store.latest.odometry;
  const markerSize = Math.max(7, Math.min(13, width / 35));
  if (envelope?.channel === "odometry") {
    const pose = canvasPoint(
      grid,
      { x: envelope.payload.x_m, y: envelope.payload.y_m },
      width,
      height,
    );
    if (pose) {
      drawPoseMarker(
        context,
        pose,
        envelope.payload.yaw_rad,
        markerSize,
        grid,
        { fill: "#3b82f6", stroke: "#dbeafe", lineWidth: 1.5 },
      );
    }
  }

  const localizationEnvelope = store.latest.localization;
  const localization =
    localizationEnvelope?.channel === "localization"
      ? localizationEnvelope.payload
      : store.localization?.latest_pose;
  if (localization && localizationEnabled.value) {
    const pose = canvasPoint(
      grid,
      { x: localization.x_m, y: localization.y_m },
      width,
      height,
    );
    if (pose) {
      drawPoseMarker(
        context,
        pose,
        localization.yaw_rad,
        markerSize + 4,
        grid,
        { stroke: "#34d399", lineWidth: 2.25 },
      );
    }
  }

  const truthEnvelope = store.latest.simulation;
  const truth =
    truthEnvelope?.channel === "simulation"
      ? truthEnvelope.payload
      : store.simulation?.latest_state;
  const origin = odomOriginInWorld.value;
  if (!truth || !origin) return;
  const truthInOdom = worldPointToOdom({ x: truth.x_m, y: truth.y_m }, origin);
  const truthPose = canvasPoint(grid, truthInOdom, width, height);
  if (!truthPose) return;
  drawPoseMarker(
    context,
    truthPose,
    worldYawToOdom(truth.yaw_rad, origin.yaw),
    markerSize + 2,
    grid,
    { stroke: truth.collision ? "#f59e0b" : "#c084fc", lineWidth: 2 },
  );
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

watch(
  () => store.latest.odometry?.payload.header.sequence,
  () => {
    const envelope = store.latest.odometry;
    if (
      envelope?.channel === "odometry" &&
      store.mappingSession?.state === "active"
    ) {
      const point = { x: envelope.payload.x_m, y: envelope.payload.y_m };
      const previous = odometryTrail.value.at(-1);
      const minimumDistance = (map.value?.resolution_m ?? 0.05) / 2;
      if (
        !previous ||
        Math.hypot(point.x - previous.x, point.y - previous.y) >=
          minimumDistance
      ) {
        odometryTrail.value.push(point);
        if (odometryTrail.value.length > 1000) odometryTrail.value.shift();
      }
    }
    scheduleDraw();
  },
);

watch(() => store.latest.simulation?.payload.header.sequence, scheduleDraw);
watch(() => store.latest.localization?.payload.header.sequence, scheduleDraw);
watch(() => store.localization?.latest_pose?.header.sequence, scheduleDraw);

watch([simulationWorld, odomOriginInWorld], scheduleDraw);

watch(
  [() => store.mappingSession?.session_id, () => store.mapClearGeneration],
  () => {
    odometryTrail.value = [];
    scheduleDraw();
  },
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
