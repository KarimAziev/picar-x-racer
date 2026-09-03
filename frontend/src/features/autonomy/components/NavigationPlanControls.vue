<template>
  <section
    class="rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900"
  >
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold">Navigation goal</h2>
        <p class="text-[0.68rem] text-surface-500 dark:text-surface-400">
          Planning preview only; this never moves the vehicle
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
        {{ plan.reason }}
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
          <dd>{{ plan.path.length }}</dd>
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

      <div class="mt-3 flex flex-wrap gap-2">
        <Button
          label="Clear preview"
          icon="pi pi-times"
          severity="secondary"
          size="small"
          outlined
          :loading="store.navigationPlanLoading"
          @click="store.clearNavigationPlan()"
        />
        <span
          v-if="plan.state === 'ready'"
          class="self-center text-[0.68rem] text-surface-500"
        >
          Start navigation will be added with the path follower.
        </span>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useAutonomyStore, type NavigationPoint } from "@/features/autonomy";

const store = useAutonomyStore();
const plan = computed(() => store.navigationPlan);
const stateLabel = computed(() => {
  if (store.navigationPlanLoading) return "Planning…";
  if (!plan.value) return "Checking…";
  return `Plan: ${plan.value.state}`;
});
const stateSeverity = computed(() => {
  if (plan.value?.state === "ready") return "success";
  if (plan.value?.state === "rejected" || plan.value?.state === "failed") {
    return "danger";
  }
  return "secondary";
});
const messageClasses = computed(() =>
  plan.value?.state === "ready"
    ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100"
    : "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-100",
);

const formatPoint = (point: NavigationPoint) =>
  `${point.x_m.toFixed(2)}, ${point.y_m.toFixed(2)} m`;
</script>
