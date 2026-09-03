<template>
  <section
    class="rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900"
  >
    <ConfirmPopup group="simulation-reset" />
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold">Simulation environment</h2>
        <p class="text-[0.68rem] text-surface-500 dark:text-surface-400">
          One Ackermann plant for motion, steering, encoders, IMU, and LiDAR
        </p>
      </div>
      <Tag :severity="statusSeverity" :value="statusLabel" />
    </div>

    <div
      v-if="store.simulationLoading"
      class="mt-3 flex items-center gap-2 text-xs text-surface-500"
    >
      <ProgressSpinner class="h-4 w-4" stroke-width="5" />
      Checking simulation runtime…
    </div>

    <template v-else-if="status?.enabled">
      <div
        class="mt-3 rounded-lg border px-3 py-2 text-xs"
        :class="isolationClasses"
        role="status"
      >
        <div class="font-semibold">{{ isolationTitle }}</div>
        <div class="mt-0.5 opacity-80">{{ isolationDetail }}</div>
      </div>

      <div
        class="mt-2 rounded-lg bg-blue-50 px-3 py-2 text-[0.7rem] leading-relaxed text-blue-900 dark:bg-blue-950 dark:text-blue-100"
      >
        The map marker follows command-driven odometry. Throttle moves it;
        steering changes its curvature once the Ackermann vehicle is moving.
        Releasing throttle keeps the pose stationary.
      </div>

      <dl
        v-if="status.latest_state"
        class="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs sm:grid-cols-3 xl:grid-cols-2"
      >
        <div>
          <dt class="text-surface-500">Ground truth</dt>
          <dd>
            {{ format(status.latest_state.x_m) }},
            {{ format(status.latest_state.y_m) }} m
          </dd>
        </div>
        <div>
          <dt class="text-surface-500">Heading</dt>
          <dd>{{ degrees(status.latest_state.yaw_rad) }}°</dd>
        </div>
        <div>
          <dt class="text-surface-500">Speed</dt>
          <dd>{{ format(status.latest_state.linear_speed_mps) }} m/s</dd>
        </div>
        <div>
          <dt class="text-surface-500">Steering</dt>
          <dd>{{ degrees(status.latest_state.steering_angle_rad) }}°</dd>
        </div>
        <div>
          <dt class="text-surface-500">Encoder</dt>
          <dd>
            {{ status.latest_state.encoder_ticks.toLocaleString() }} ticks
          </dd>
        </div>
        <div>
          <dt class="text-surface-500">Plant frames</dt>
          <dd>{{ status.published_updates.toLocaleString() }}</dd>
        </div>
        <div>
          <dt class="text-surface-500">LiDAR frames</dt>
          <dd>{{ status.lidar_published_updates.toLocaleString() }}</dd>
        </div>
        <div>
          <dt class="text-surface-500">World</dt>
          <dd>{{ formatScenario(status.world?.scenario) }}</dd>
        </div>
        <div>
          <dt class="text-surface-500">Sensor model</dt>
          <dd>{{ sensorModelLabel }}</dd>
        </div>
      </dl>
      <div v-else class="mt-3 text-xs text-surface-500">
        Waiting for the first synchronized plant frame.
      </div>

      <div
        v-if="rawEstimationError || fusedEstimationError"
        class="mt-2 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-xs text-violet-950 dark:border-violet-800 dark:bg-violet-950 dark:text-violet-100"
        role="status"
      >
        <div class="font-semibold">
          Estimator accuracy · simulation reference
        </div>
        <dl class="mt-1 grid grid-cols-[auto_1fr_1fr] gap-x-3 gap-y-1">
          <dt class="text-violet-700 dark:text-violet-300">Source</dt>
          <dt class="text-violet-700 dark:text-violet-300">Position</dt>
          <dt class="text-violet-700 dark:text-violet-300">Heading</dt>
          <template v-if="rawEstimationError">
            <dd>Raw odometry</dd>
            <dd>{{ formatErrorDistance(rawEstimationError.positionM) }}</dd>
            <dd>{{ degrees(rawEstimationError.headingRad) }}°</dd>
          </template>
          <template v-if="fusedEstimationError">
            <dd>Fused pose</dd>
            <dd>{{ formatErrorDistance(fusedEstimationError.positionM) }}</dd>
            <dd>{{ degrees(fusedEstimationError.headingRad) }}°</dd>
          </template>
        </dl>
        <p class="mt-1 opacity-75">
          Distance from the simulator's exact pose—not an application fault.
          Blue is raw odometry, green is fused pose, and purple is exact truth.
        </p>
      </div>

      <div
        v-if="status.latest_state?.collision"
        class="mt-2 rounded-md bg-amber-50 p-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-200"
        role="status"
      >
        Collision envelope reached an obstacle. The plant rejected forward
        translation; steer away or reverse.
      </div>

      <div class="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span class="text-[0.68rem] text-surface-500">{{ updatedLabel }}</span>
        <Button
          label="Reset pose"
          icon="pi pi-refresh"
          severity="secondary"
          size="small"
          outlined
          :disabled="!status.physical_drive_isolated"
          :loading="store.simulationResetting"
          @click="confirmReset"
        />
      </div>
    </template>

    <div
      v-else
      class="mt-3 rounded-lg bg-surface-100 p-3 text-xs leading-relaxed dark:bg-surface-800"
    >
      <p>
        Enable <span class="font-semibold">Coherent simulation</span> to make
        keyboard commands drive one synchronized steering, encoder, IMU, and
        world-aware LiDAR source. Physical output remains selected while this
        environment is disabled.
      </p>
      <p
        v-if="simulationPrerequisiteError"
        class="mt-2 text-amber-700 dark:text-amber-300"
      >
        {{ simulationPrerequisiteError }}
      </p>
      <Button
        class="mt-3"
        label="Enable synchronized drive"
        icon="pi pi-desktop"
        size="small"
        :disabled="Boolean(simulationPrerequisiteError)"
        :loading="simulationToggleLoading"
        @click="enableSynchronizedDrive"
      />
    </div>

    <div
      v-if="store.simulationError || status?.error"
      class="mt-2 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-950 dark:text-red-200"
      role="alert"
    >
      {{ store.simulationError || status?.error }}
      <span v-if="status" class="block opacity-80">
        Last known state remains visible above.
      </span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import ConfirmPopup from "primevue/confirmpopup";
import { useConfirm } from "primevue/useconfirm";
import { useAutonomyStore } from "@/features/autonomy";
import {
  calculatePoseError,
  worldPointToOdom,
  worldYawToOdom,
} from "@/features/autonomy/mapGeometry";
import { useRobotStore } from "@/features/settings/stores";

const store = useAutonomyStore();
const robotStore = useRobotStore();
const confirm = useConfirm();
const now = ref(Date.now());
const simulationToggleLoading = ref(false);
let refreshTimer: ReturnType<typeof setInterval> | null = null;
const status = computed(() => store.simulation);
const truthPoseInOdom = computed(() => {
  const streamedTruth = store.latest.simulation;
  const origin = status.value?.odom_origin_in_world;
  const truth =
    streamedTruth?.channel === "simulation"
      ? streamedTruth.payload
      : status.value?.latest_state;
  if (!origin || !truth) return null;
  const truthInOdom = worldPointToOdom(
    { x: truth.x_m, y: truth.y_m },
    { x: origin.x_m, y: origin.y_m, yaw: origin.yaw_rad },
  );
  return {
    ...truthInOdom,
    yaw: worldYawToOdom(truth.yaw_rad, origin.yaw_rad),
  };
});
const rawEstimationError = computed(() => {
  const odometry = store.latest.odometry;
  if (odometry?.channel !== "odometry" || !truthPoseInOdom.value) return null;
  return calculatePoseError(
    {
      x: odometry.payload.x_m,
      y: odometry.payload.y_m,
      yaw: odometry.payload.yaw_rad,
    },
    truthPoseInOdom.value,
  );
});
const fusedEstimationError = computed(() => {
  const localization = store.latest.localization;
  const pose =
    store.localization?.enabled && localization?.channel === "localization"
      ? localization.payload
      : store.localization?.latest_pose;
  if (!pose || !truthPoseInOdom.value) return null;
  return calculatePoseError(
    { x: pose.x_m, y: pose.y_m, yaw: pose.yaw_rad },
    truthPoseInOdom.value,
  );
});

const simulationPrerequisiteError = computed(() => {
  const { motion_control: motion, ackermann_odometry: odometry } =
    robotStore.data;
  if (!motion.enabled)
    return "Enable motion control and restart the backend once.";
  if (
    motion.max_forward_speed_mps === null ||
    motion.max_reverse_speed_mps === null
  ) {
    return "Configure forward and reverse speed calibration first.";
  }
  if (!odometry.enabled) {
    return "Enable Ackermann odometry and restart the backend once.";
  }
  if (
    odometry.wheelbase_m === null ||
    odometry.wheel_radius_m === null ||
    odometry.encoder_ticks_per_revolution === null
  ) {
    return "Configure wheelbase, wheel radius, and encoder resolution first.";
  }
  return null;
});

const statusSeverity = computed(() => {
  if (store.simulationError || status.value?.error) return "danger";
  if (!status.value?.enabled) return "secondary";
  if (!status.value.physical_drive_isolated) return "danger";
  return status.value.running ? "success" : "warn";
});
const statusLabel = computed(() => {
  if (!status.value) return "Checking…";
  if (!status.value.enabled) return "Disabled";
  if (!status.value.physical_drive_isolated) return "Isolation fault";
  return status.value.running ? "Live · isolated" : "Stopped · isolated";
});
const isolationTitle = computed(() =>
  status.value?.physical_drive_isolated
    ? "Physical drive isolated"
    : "Physical drive is still selectable",
);
const isolationDetail = computed(() =>
  status.value?.physical_drive_isolated
    ? "Resolved commands go only to the virtual drive sink. Mode changes still disarm and invalidate older commands."
    : "Do not arm motion until the backend confirms isolation.",
);
const isolationClasses = computed(() =>
  status.value?.physical_drive_isolated
    ? "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-100"
    : "border-red-300 bg-red-50 text-red-900 dark:border-red-700 dark:bg-red-950 dark:text-red-100",
);
const updatedLabel = computed(() => {
  if (store.simulationLastUpdatedAt === null) return "No runtime response yet";
  const seconds = Math.max(
    0,
    Math.floor((now.value - store.simulationLastUpdatedAt) / 1000),
  );
  if (store.simulationError)
    return `Status offline · last update ${seconds}s ago`;
  return seconds < 2 ? "Runtime status live" : `Updated ${seconds}s ago`;
});
const sensorModelLabel = computed(() => {
  const model = status.value?.sensor_imperfections;
  if (!model?.enabled) return "Ideal";
  return `Seeded imperfections · ${model.random_seed}`;
});

const format = (value: number) => value.toFixed(2);
const formatErrorDistance = (value: number) =>
  value < 0.01 ? `${(value * 1000).toFixed(1)} mm` : `${value.toFixed(3)} m`;
const degrees = (radians: number) => ((radians * 180) / Math.PI).toFixed(1);
const formatScenario = (scenario?: string) =>
  scenario ? scenario.replaceAll("_", " ") : "No LiDAR world";
const enableSynchronizedDrive = async () => {
  if (simulationPrerequisiteError.value) return;
  simulationToggleLoading.value = true;
  try {
    await robotStore.updatePartialData({
      coherent_simulation: {
        ...robotStore.data.coherent_simulation,
        enabled: true,
      },
    });
    await Promise.all([
      store.refreshSimulation(),
      store.refreshMappingSession(),
    ]);
  } finally {
    simulationToggleLoading.value = false;
  }
};
const confirmReset = (event: MouseEvent) =>
  confirm.require({
    group: "simulation-reset",
    target: event.currentTarget as HTMLElement,
    icon: "pi pi-refresh",
    message:
      "Disarm motion, discard the simulated trajectory, and restore the configured initial pose?",
    rejectProps: {
      label: "Cancel",
      severity: "secondary",
      outlined: true,
    },
    acceptProps: { label: "Reset simulation", severity: "danger" },
    accept: () => void store.resetSimulation(),
  });

onMounted(() => {
  void store.refreshSimulation();
  refreshTimer = setInterval(() => {
    now.value = Date.now();
    if (!store.simulationLoading && !store.simulationResetting) {
      void store.refreshSimulation();
    }
  }, 1000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>
