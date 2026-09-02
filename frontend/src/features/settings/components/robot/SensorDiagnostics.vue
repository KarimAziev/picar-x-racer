<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-3">
      <div class="text-xs text-surface-500 dark:text-surface-400">
        Hardware-rate acquisition with a bounded 5 Hz browser preview.
      </div>
      <Tag
        :severity="store.connected ? 'success' : 'secondary'"
        :value="store.connected ? 'Telemetry connected' : 'Telemetry offline'"
      />
    </div>

    <div v-if="store.error" class="text-sm text-red-500">
      {{ store.error }}
    </div>
    <div v-else-if="store.loading" class="flex items-center gap-2 text-sm">
      <ProgressSpinner class="w-5 h-5" strokeWidth="5" />
      Loading sensor status…
    </div>

    <div v-else class="grid gap-2 md:grid-cols-3">
      <div
        v-for="sensor in store.sensors"
        :key="sensor.sensor"
        class="rounded-lg border border-surface-200 p-3 dark:border-surface-700"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="font-semibold uppercase">{{ sensor.sensor }}</span>
          <Tag
            :severity="sensorSeverity(sensor)"
            :value="sensorState(sensor)"
          />
        </div>
        <div class="mt-2 text-xs text-surface-500 dark:text-surface-400">
          {{ sensor.published_messages.toLocaleString() }} messages published
        </div>
        <div v-if="sensor.error" class="mt-2 text-xs text-red-500 break-words">
          {{ sensor.error }}
        </div>
        <div v-if="latestSummary(sensor.sensor)" class="mt-2 text-xs">
          {{ latestSummary(sensor.sensor) }}
        </div>
      </div>
    </div>

    <div
      v-if="odometrySummary"
      class="rounded-lg bg-surface-100 px-3 py-2 text-xs dark:bg-surface-800"
    >
      <span class="font-semibold">Odometry:</span>
      {{ odometrySummary }}
    </div>
    <div
      v-if="store.localization"
      class="rounded-lg border border-surface-200 px-3 py-2 text-xs dark:border-surface-700"
    >
      <div class="flex flex-wrap items-center justify-between gap-2">
        <span class="font-semibold">Pose fusion</span>
        <Tag :severity="localizationSeverity" :value="localizationState" />
      </div>
      <div v-if="localizationSummary" class="mt-1">
        {{ localizationSummary }}
      </div>
      <div
        v-if="store.localization.error || store.localizationError"
        class="mt-1 break-words text-red-500"
      >
        {{ store.localization.error || store.localizationError }}
      </div>
      <div
        v-else-if="store.localization.enabled"
        class="mt-1 text-surface-500 dark:text-surface-400"
      >
        {{ store.localization.imu_updates_used.toLocaleString() }} gyro updates
        · {{ store.localization.corrections_applied.toLocaleString() }} external
        corrections
      </div>
    </div>
    <div
      v-if="safetySummary"
      class="rounded-lg px-3 py-2 text-xs"
      :class="
        safetyBlocked
          ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200'
          : 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200'
      "
    >
      <span class="font-semibold">Forward safety:</span>
      {{ safetySummary }}
    </div>
    <template v-if="showPreviews">
      <LidarScanPreview />
      <OccupancyGridPreview />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from "vue";
import {
  useAutonomyStore,
  type SensorPublisherStatus,
  type SensorName,
} from "@/features/autonomy";
import LidarScanPreview from "@/features/settings/components/robot/LidarScanPreview.vue";
import OccupancyGridPreview from "@/features/settings/components/robot/OccupancyGridPreview.vue";

withDefaults(
  defineProps<{
    showPreviews?: boolean;
  }>(),
  { showPreviews: true },
);

const store = useAutonomyStore();
let statusTimer: ReturnType<typeof setInterval> | null = null;

const formatNumber = (value: number, digits = 2) => value.toFixed(digits);

const sensorSeverity = (sensor: SensorPublisherStatus) => {
  if (!sensor.enabled) return "secondary";
  if (sensor.error) return "danger";
  if (sensor.running) return "success";
  return "warn";
};

const sensorState = (sensor: SensorPublisherStatus) => {
  if (!sensor.enabled) return "Disabled";
  if (sensor.error) return "Error";
  if (sensor.running) return "Running";
  return "Waiting";
};

const latestSummary = (sensor: SensorName) => {
  const envelope = store.latest[sensor];
  if (!envelope) return null;
  switch (envelope.channel) {
    case "lidar": {
      const returns = envelope.payload.ranges_m.filter(
        (range): range is number => range !== null,
      );
      const nearest = returns.length ? Math.min(...returns) : null;
      return nearest === null
        ? "No valid returns"
        : `${returns.length} returns · nearest ${formatNumber(nearest)} m`;
    }
    case "imu":
      return `yaw rate ${formatNumber(envelope.payload.angular_velocity_z_radps)} rad/s`;
    case "encoder": {
      const readings = [
        envelope.payload.left &&
          `L ${envelope.payload.left.ticks} · Δ ${envelope.payload.left.delta_ticks}`,
        envelope.payload.right &&
          `R ${envelope.payload.right.ticks} · Δ ${envelope.payload.right.delta_ticks}`,
      ].filter(Boolean);
      return readings.join(" · ");
    }
  }
  return null;
};

const odometrySummary = computed(() => {
  const envelope = store.latest.odometry;
  if (!envelope || envelope.channel !== "odometry") return null;
  const { x_m, y_m, yaw_rad, linear_speed_mps } = envelope.payload;
  return `x ${formatNumber(x_m)} m · y ${formatNumber(y_m)} m · yaw ${formatNumber(yaw_rad)} rad · ${formatNumber(linear_speed_mps)} m/s`;
});

const localizationSeverity = computed(() => {
  const status = store.localization;
  if (!status?.enabled) return "secondary";
  if (status.error || store.localizationError) return "danger";
  return status.running ? "success" : "warn";
});

const localizationState = computed(() => {
  const status = store.localization;
  if (!status?.enabled) return "Disabled";
  if (status.error || store.localizationError) return "Error";
  return status.running ? "Running" : "Waiting";
});

const localizationSummary = computed(() => {
  const envelope = store.latest.localization;
  const pose =
    store.localization?.enabled && envelope?.channel === "localization"
      ? envelope.payload
      : store.localization?.latest_pose;
  if (!pose) {
    return store.localization?.enabled
      ? "Waiting for the first odometry update…"
      : "Enable pose estimation to fuse wheel odometry and fresh gyro yaw rate.";
  }
  const positionStddevM = Math.sqrt(pose.position_variance_m2);
  const headingStddevDeg = (Math.sqrt(pose.yaw_variance_rad2) * 180) / Math.PI;
  const mode = pose.fusion_mode.replace("_", " + ");
  return `x ${formatNumber(pose.x_m)} m · y ${formatNumber(pose.y_m)} m · yaw ${formatNumber(pose.yaw_rad)} rad · ${mode} · uncertainty ±${formatNumber(positionStddevM, 3)} m / ±${formatNumber(headingStddevDeg, 1)}°`;
});

const safetyBlocked = computed(() => {
  const envelope = store.latest.safety;
  return envelope?.channel === "safety" && envelope.payload.forward_blocked;
});

const safetySummary = computed(() => {
  const envelope = store.latest.safety;
  if (!envelope || envelope.channel !== "safety") return null;
  if (envelope.payload.reason) return envelope.payload.reason;
  return `clear · up to ${formatNumber(envelope.payload.max_forward_speed_mps)} m/s`;
});

onMounted(() => {
  store.initialize();
  statusTimer = setInterval(
    () =>
      void Promise.all([store.refreshStatus(), store.refreshLocalization()]),
    2500,
  );
});

onUnmounted(() => {
  if (statusTimer) clearInterval(statusTimer);
  store.cleanup();
});
</script>
