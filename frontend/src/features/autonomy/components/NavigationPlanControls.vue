<template>
  <section
    class="rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900"
  >
    <ConfirmPopup group="navigation" />
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold">Navigation goal</h2>
        <p class="text-[0.68rem] text-surface-500 dark:text-surface-400">
          Review a collision-aware route before explicitly starting it
        </p>
      </div>
      <Tag :severity="stateSeverity" :value="stateLabel" />
    </div>

    <div
      v-if="store.navigationPlanError"
      class="mt-2 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-950 dark:text-red-200"
    >
      {{ store.navigationPlanError }}
    </div>
    <div
      v-if="store.navigationExecutionError"
      class="mt-2 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-950 dark:text-red-200"
    >
      {{ store.navigationExecutionError }}
    </div>

    <div
      v-if="!plan?.goal"
      class="mt-3 rounded-lg border border-dashed border-surface-300 p-3 text-xs leading-relaxed text-surface-600 dark:border-surface-700 dark:text-surface-300"
    >
      Click an observed free point on the map. The planner inflates obstacles by
      0.20 m, rejects unknown space, and draws a route for review.
    </div>

    <template v-else>
      <div
        class="mt-3 rounded-lg p-3 text-xs leading-relaxed"
        :class="messageClasses"
      >
        {{ planMessage }}
      </div>

      <dl class="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
        <div>
          <dt class="text-surface-500">Goal</dt>
          <dd>{{ formatPoint(plan.goal) }}</dd>
        </div>
        <div>
          <dt class="text-surface-500">Clearance</dt>
          <dd>{{ plan.clearance_m.toFixed(2) }} m</dd>
        </div>
        <div v-if="plan.state === 'ready'">
          <dt class="text-surface-500">Route length</dt>
          <dd>{{ plan.path_length_m.toFixed(2) }} m</dd>
        </div>
        <div v-if="plan.state === 'ready'">
          <dt class="text-surface-500">Waypoints</dt>
          <dd>
            {{ plan.path.length }}
            <span v-if="plan.smoothed" class="text-surface-500">
              (from {{ plan.raw_waypoint_count }})
            </span>
          </dd>
        </div>
        <div v-if="plan.state === 'ready'">
          <dt class="text-surface-500">Drive geometry</dt>
          <dd>
            {{ plan.geometry_validated ? "Validated" : "Not configured" }}
          </dd>
        </div>
        <div v-if="plan.minimum_turning_radius_m !== null">
          <dt class="text-surface-500">Minimum turn radius</dt>
          <dd>{{ plan.minimum_turning_radius_m.toFixed(2) }} m</dd>
        </div>
        <div v-if="plan.max_curvature_per_m !== null">
          <dt class="text-surface-500">Route curvature</dt>
          <dd>
            {{ formatCurvature(plan.max_curvature_per_m) }}
          </dd>
        </div>
        <div v-if="plan.initial_heading_error_deg !== null">
          <dt class="text-surface-500">Initial heading offset</dt>
          <dd>{{ formatSigned(plan.initial_heading_error_deg) }}°</dd>
        </div>
        <div v-if="plan.pose_source">
          <dt class="text-surface-500">Start pose</dt>
          <dd>
            {{
              plan.pose_source === "localization"
                ? "Fused localization"
                : "Raw odometry"
            }}
          </dd>
        </div>
        <div v-if="plan.map_sequence !== null">
          <dt class="text-surface-500">Map snapshot</dt>
          <dd>#{{ plan.map_sequence.toLocaleString() }}</dd>
        </div>
      </dl>
      <p
        v-if="plan.state === 'ready'"
        class="mt-2 text-[0.68rem] leading-relaxed text-surface-500"
      >
        This route is tied to map snapshot #{{ plan.map_sequence }}. Any map
        update stops execution and requires another review.
      </p>

      <div class="mt-3 flex flex-wrap gap-2">
        <label v-if="canOfferStart" class="w-32 text-xs"
          >Maximum speed<InputNumber
            v-model="maxSpeed"
            class="mt-1"
            suffix=" m/s"
            :min="0.04"
            :max="0.5"
            :step="0.05"
            :max-fraction-digits="2"
            show-buttons
            fluid
        /></label>
        <Button
          v-if="canOfferStart"
          label="Review and start"
          icon="pi pi-compass"
          severity="danger"
          size="small"
          class="self-end"
          :disabled="!canStart"
          :loading="store.navigationExecutionLoading"
          @click="confirmStart"
        />
        <Button
          v-if="execution?.state === 'running'"
          label="Pause"
          icon="pi pi-pause"
          severity="warn"
          size="small"
          :loading="store.navigationExecutionLoading"
          @click="store.runNavigationAction('pause')"
        />
        <Button
          v-if="execution?.state === 'paused'"
          label="Resume"
          icon="pi pi-play"
          size="small"
          :loading="store.navigationExecutionLoading"
          @click="store.runNavigationAction('resume')"
        />
        <Button
          v-if="navigationActive"
          label="Cancel navigation"
          icon="pi pi-stop"
          severity="danger"
          size="small"
          :loading="store.navigationExecutionLoading"
          @click="store.runNavigationAction('cancel')"
        />
        <Button
          v-if="!navigationActive"
          label="Clear preview"
          icon="pi pi-times"
          severity="secondary"
          size="small"
          outlined
          :loading="store.navigationPlanLoading"
          @click="store.clearNavigationPlan()"
        />
      </div>

      <div v-if="execution?.action_id" class="mt-3 text-xs">
        <div class="flex justify-between">
          <span>{{ execution.progress_m.toFixed(2) }} m followed</span>
          <span>{{ execution.remaining_m.toFixed(2) }} m left</span>
        </div>
        <ProgressBar
          class="mt-1 h-2"
          :value="executionProgress"
          :show-value="false"
        />
        <dl class="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-surface-500">
          <div>
            <dt>Command</dt>
            <dd>
              {{ execution.commanded_speed_mps.toFixed(2) }} m/s ·
              {{ formatSigned(execution.steering_angle_deg) }}°
            </dd>
          </div>
          <div>
            <dt>Cross-track error</dt>
            <dd>{{ execution.cross_track_error_m.toFixed(2) }} m</dd>
          </div>
        </dl>
        <div
          v-if="execution.reason"
          class="mt-2 rounded bg-surface-100 p-2 dark:bg-surface-800"
        >
          {{ execution.reason }}
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import ConfirmPopup from "primevue/confirmpopup";
import { useConfirm } from "primevue/useconfirm";
import { useAutonomyStore, type NavigationPoint } from "@/features/autonomy";

const store = useAutonomyStore();
const confirm = useConfirm();
const maxSpeed = ref(0.15);
let timer: ReturnType<typeof setInterval> | null = null;
const plan = computed(() => store.navigationPlan);
const execution = computed(() => {
  const currentPlan = plan.value;
  const currentExecution = store.navigationExecution;
  if (
    !currentPlan?.goal ||
    !currentExecution?.goal ||
    currentExecution.map_sequence !== currentPlan.map_sequence ||
    Math.abs(currentExecution.goal.x_m - currentPlan.goal.x_m) > 1e-6 ||
    Math.abs(currentExecution.goal.y_m - currentPlan.goal.y_m) > 1e-6
  ) {
    return null;
  }
  return currentExecution;
});
const navigationActive = computed(() =>
  ["running", "paused"].includes(execution.value?.state ?? ""),
);
const canStart = computed(
  () =>
    plan.value?.state === "ready" &&
    plan.value.geometry_validated &&
    execution.value?.available !== false &&
    maxSpeed.value > 0 &&
    !store.navigationExecutionLoading,
);
const canOfferStart = computed(
  () =>
    plan.value?.state === "ready" &&
    !navigationActive.value &&
    execution.value?.state !== "succeeded",
);
const stateLabel = computed(() => {
  if (execution.value?.action_id) return `Navigation: ${execution.value.state}`;
  if (store.navigationPlanLoading) return "Planning…";
  if (!plan.value) return "Checking…";
  return `Plan: ${plan.value.state}`;
});
const stateSeverity = computed(() => {
  if (execution.value?.state === "running") return "success";
  if (execution.value?.state === "paused") return "warn";
  if (execution.value?.state === "succeeded") return "success";
  if (["blocked", "failed"].includes(execution.value?.state ?? "")) {
    return "danger";
  }
  if (plan.value?.state === "ready") return "success";
  if (plan.value?.state === "rejected" || plan.value?.state === "failed") {
    return "danger";
  }
  return "secondary";
});
const messageClasses = computed(() =>
  ["blocked", "failed"].includes(execution.value?.state ?? "") ||
  plan.value?.state !== "ready"
    ? "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-100"
    : execution.value?.state === "paused"
      ? "bg-amber-50 text-amber-900 dark:bg-amber-950 dark:text-amber-100"
      : "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100",
);
const planMessage = computed(() => {
  if (navigationActive.value) {
    return execution.value?.state === "paused"
      ? "Navigation is paused and the drive is disarmed."
      : "The reviewed route is being executed through the motion arbiter.";
  }
  return execution.value?.action_id
    ? execution.value.reason
    : plan.value?.reason;
});

const formatPoint = (point: NavigationPoint) =>
  `${point.x_m.toFixed(2)}, ${point.y_m.toFixed(2)} m`;
const formatSigned = (value: number) =>
  (value > 0 ? "+" : "") + value.toFixed(1);
const formatCurvature = (curvaturePerM: number) =>
  curvaturePerM < 1e-6
    ? "Straight"
    : `${curvaturePerM.toFixed(2)} m⁻¹ (${(1 / curvaturePerM).toFixed(2)} m radius)`;
const executionProgress = computed(() =>
  Math.min(
    100,
    execution.value?.path_length_m
      ? (execution.value.progress_m / execution.value.path_length_m) * 100
      : 0,
  ),
);
const confirmStart = (event: MouseEvent) =>
  confirm.require({
    group: "navigation",
    target: event.currentTarget as HTMLElement,
    icon: "pi pi-compass",
    message: `Enter autonomous mode and follow this reviewed route at up to ${maxSpeed.value.toFixed(2)} m/s? LiDAR safety, localization freshness, and the motion arbiter remain authoritative.`,
    rejectProps: { label: "Cancel", severity: "secondary", outlined: true },
    acceptProps: { label: "Start navigation", severity: "danger" },
    accept: () => void store.startNavigation(maxSpeed.value),
  });

onMounted(() => {
  void store.refreshNavigationExecution();
  timer = setInterval(() => void store.refreshNavigationExecution(), 250);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>
