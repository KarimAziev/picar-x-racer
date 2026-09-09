<template>
  <section
    class="rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900"
  >
    <ConfirmPopup group="navigation-mission" />
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold">Navigation mission</h2>
        <p class="text-[0.68rem] text-surface-500 dark:text-surface-400">
          Add ordered map targets, review every leg, then explicitly start
        </p>
      </div>
      <Tag :severity="stateSeverity" :value="stateLabel" />
    </div>

    <div
      v-if="missionError"
      class="mt-2 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-950 dark:text-red-200"
    >
      {{ missionError }}
    </div>
    <div
      v-if="mappingActive"
      class="mt-2 rounded-md bg-amber-50 p-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-100"
    >
      Pause or finish mapping before reviewing and starting a mission.
    </div>

    <div class="mt-3 flex flex-wrap items-end gap-3">
      <div>
        <div class="mb-1 text-xs text-surface-500">Mode</div>
        <ButtonGroup>
          <Button
            label="Once"
            size="small"
            :outlined="store.navigationMissionMode !== 'once'"
            :aria-pressed="store.navigationMissionMode === 'once'"
            :disabled="missionActive"
            @click="setMode('once')"
          />
          <Button
            label="Loop"
            icon="pi pi-refresh"
            size="small"
            :outlined="store.navigationMissionMode !== 'loop'"
            :aria-pressed="store.navigationMissionMode === 'loop'"
            :disabled="missionActive"
            @click="setMode('loop')"
          />
        </ButtonGroup>
      </div>
      <label v-if="store.navigationMissionMode === 'loop'" class="w-28 text-xs">
        Laps
        <InputNumber
          class="mt-1"
          :model-value="store.navigationMissionLapCount"
          :min="1"
          :max="100"
          show-buttons
          fluid
          :disabled="missionActive"
          @update:model-value="setLapCount"
        />
      </label>
      <label class="w-32 text-xs">
        Maximum speed
        <InputNumber
          v-model="maxSpeed"
          class="mt-1"
          suffix=" m/s"
          :min="0.04"
          :max="0.5"
          :step="0.05"
          :max-fraction-digits="2"
          show-buttons
          fluid
          :disabled="missionActive"
        />
      </label>
    </div>

    <div
      v-if="store.missionTargets.length === 0"
      class="mt-3 rounded-lg border border-dashed border-surface-300 p-3 text-xs leading-relaxed text-surface-600 dark:border-surface-700 dark:text-surface-300"
    >
      Click observed free locations on the map. Each click adds the next
      numbered stopping target.
    </div>
    <ol v-else class="mt-3 flex flex-col gap-1.5">
      <li
        v-for="(target, index) in store.missionTargets"
        :key="`${index}-${target.x_m}-${target.y_m}`"
        class="flex items-center gap-2 rounded-md border border-surface-200 px-2 py-1.5 text-xs dark:border-surface-700"
        :class="{
          'border-amber-400 bg-amber-50 dark:border-amber-600 dark:bg-amber-950':
            execution?.active_target_index === index,
        }"
      >
        <span
          class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-800 font-semibold text-white dark:bg-surface-100 dark:text-surface-900"
        >{{ index + 1 }}</span>
        <span class="min-w-0 flex-1 font-mono">{{ formatPoint(target) }}</span>
        <Button
          icon="pi pi-arrow-up"
          text
          rounded
          size="small"
          aria-label="Move target earlier"
          :disabled="missionActive || index === 0"
          @click="store.moveMissionTarget(index, -1)"
        />
        <Button
          icon="pi pi-arrow-down"
          text
          rounded
          size="small"
          aria-label="Move target later"
          :disabled="missionActive || index === store.missionTargets.length - 1"
          @click="store.moveMissionTarget(index, 1)"
        />
        <Button
          icon="pi pi-times"
          text
          rounded
          severity="danger"
          size="small"
          aria-label="Remove target"
          :disabled="missionActive"
          @click="store.removeMissionTarget(index)"
        />
      </li>
    </ol>

    <div
      v-if="plan?.reason"
      class="mt-3 rounded-lg p-2 text-xs leading-relaxed"
      :class="planMessageClasses"
    >
      {{ plan.reason }}
    </div>

    <dl
      v-if="plan?.state === 'ready'"
      class="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs"
    >
      <div>
        <dt class="text-surface-500">Preflight legs</dt>
        <dd>{{ plan.legs.length }}</dd>
      </div>
      <div>
        <dt class="text-surface-500">Map snapshot</dt>
        <dd>#{{ plan.map_sequence?.toLocaleString() }}</dd>
      </div>
      <div>
        <dt class="text-surface-500">Estimated distance</dt>
        <dd>{{ plan.total_path_length_m.toFixed(2) }} m</dd>
      </div>
      <div v-if="plan.total_reverse_distance_m > 0">
        <dt class="text-surface-500">Estimated reverse</dt>
        <dd>{{ plan.total_reverse_distance_m.toFixed(2) }} m</dd>
      </div>
    </dl>

    <div class="mt-3 flex flex-wrap items-center gap-2">
      <Button
        v-if="!missionActive"
        label="Review mission"
        icon="pi pi-directions"
        size="small"
        :disabled="!canReview"
        :loading="store.navigationMissionPlanLoading"
        @click="store.reviewNavigationMission()"
      />
      <Button
        v-if="canOfferStart"
        label="Start mission"
        icon="pi pi-play"
        severity="danger"
        size="small"
        :disabled="!canStart"
        :loading="store.navigationMissionExecutionLoading"
        @click="confirmStart"
      />
      <Button
        v-if="execution?.state === 'running'"
        label="Pause"
        icon="pi pi-pause"
        severity="warn"
        size="small"
        :loading="store.navigationMissionExecutionLoading"
        @click="store.runNavigationMissionAction('pause')"
      />
      <Button
        v-if="execution?.state === 'paused'"
        label="Resume"
        icon="pi pi-play"
        size="small"
        :loading="store.navigationMissionExecutionLoading"
        @click="store.runNavigationMissionAction('resume')"
      />
      <Button
        v-if="missionActive"
        label="Cancel mission"
        icon="pi pi-stop"
        severity="danger"
        size="small"
        :loading="store.navigationMissionExecutionLoading"
        @click="store.runNavigationMissionAction('cancel')"
      />
      <Button
        v-if="!missionActive && store.missionTargets.length"
        label="Clear targets"
        icon="pi pi-trash"
        severity="secondary"
        size="small"
        :loading="store.navigationMissionPlanLoading"
        @click="store.clearNavigationMission()"
      />
    </div>

    <div v-if="execution?.mission_id" class="mt-3 text-xs">
      <div class="flex justify-between">
        <span>
          {{ execution.completed_target_visits }} /
          {{ execution.total_target_visits }} target visits
        </span>
        <span v-if="execution.mode === 'loop'">
          {{
            execution.current_lap === 0
              ? "Approach"
              : `Lap ${execution.current_lap} / ${execution.total_laps}`
          }}
        </span>
      </div>
      <ProgressBar
        class="mt-1 h-2"
        :value="executionProgress"
        :show-value="false"
      />
      <dl class="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-surface-500">
        <div v-if="execution.active_target_index !== null">
          <dt>Active target</dt>
          <dd>{{ execution.active_target_index + 1 }}</dd>
        </div>
        <div>
          <dt>Completed distance</dt>
          <dd>{{ execution.completed_distance_m.toFixed(2) }} m</dd>
        </div>
        <div v-if="liveExecution?.state === 'running'">
          <dt>Live command</dt>
          <dd>
            {{ liveExecution.commanded_speed_mps.toFixed(2) }} m/s ·
            {{ formatSigned(liveExecution.steering_angle_deg) }}°
          </dd>
        </div>
        <div v-if="liveExecution?.state === 'running'">
          <dt>Cross-track error</dt>
          <dd>{{ liveExecution.cross_track_error_m.toFixed(2) }} m</dd>
        </div>
      </dl>
      <div
        v-if="execution.reason"
        class="mt-2 rounded bg-surface-100 p-2 dark:bg-surface-800"
      >
        {{ execution.reason }}
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import ConfirmPopup from "primevue/confirmpopup";
import { useConfirm } from "primevue/useconfirm";
import {
  useAutonomyStore,
  type NavigationMissionMode,
  type NavigationPoint,
} from "@/features/autonomy";

const store = useAutonomyStore();
const confirm = useConfirm();
const maxSpeed = ref(0.15);
let timer: ReturnType<typeof setInterval> | null = null;
let polling = false;
const plan = computed(() => store.navigationMissionPlan);
const execution = computed(() => store.navigationMissionExecution);
const liveExecution = computed(() => store.navigationExecution);
const mappingActive = computed(() => store.mappingSession?.state === "active");
const missionActive = computed(() =>
  ["running", "paused"].includes(execution.value?.state ?? ""),
);
const missionError = computed(
  () =>
    store.navigationMissionPlanError ?? store.navigationMissionExecutionError ??
    store.navigationExecutionStatusError,
);
const canReview = computed(
  () =>
    store.missionTargets.length > 0 &&
    (store.navigationMissionMode !== "loop" ||
      store.missionTargets.length >= 2) &&
    !mappingActive.value &&
    !missionActive.value &&
    !store.navigationMissionPlanLoading,
);
const canOfferStart = computed(
  () => plan.value?.state === "ready" && !missionActive.value,
);
const canStart = computed(
  () =>
    canOfferStart.value &&
    execution.value?.available !== false &&
    maxSpeed.value > 0 &&
    !store.navigationMissionExecutionLoading,
);
const executionProgress = computed(() =>
  execution.value?.total_target_visits
    ? (execution.value.completed_target_visits /
        execution.value.total_target_visits) *
      100
    : 0,
);
const stateLabel = computed(() => {
  if (missionActive.value) return `Mission: ${execution.value?.state}`;
  if (store.navigationMissionPlanLoading) return "Reviewing…";
  if (execution.value?.mission_id) return `Mission: ${execution.value.state}`;
  return `Plan: ${plan.value?.state ?? "idle"}`;
});
const stateSeverity = computed(() => {
  if (["running", "succeeded"].includes(execution.value?.state ?? "")) {
    return "success";
  }
  if (execution.value?.state === "paused") return "warn";
  if (["blocked", "failed"].includes(execution.value?.state ?? "")) {
    return "danger";
  }
  if (plan.value?.state === "ready") return "success";
  if (["rejected", "failed"].includes(plan.value?.state ?? "")) return "danger";
  return "secondary";
});
const planMessageClasses = computed(() =>
  plan.value?.state === "ready"
    ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100"
    : plan.value?.state === "idle"
      ? "bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-300"
      : "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-100",
);

const formatPoint = (point: NavigationPoint) =>
  `${point.x_m.toFixed(2)}, ${point.y_m.toFixed(2)} m`;
const formatSigned = (value: number) =>
  (value > 0 ? "+" : "") + value.toFixed(1);

const setMode = (mode: NavigationMissionMode) => {
  if (store.navigationMissionMode === mode) return;
  store.navigationMissionMode = mode;
  void store.invalidateNavigationMissionReview();
};

const setLapCount = (value: number | null) => {
  const next = Math.max(1, Math.min(100, value ?? 1));
  if (store.navigationMissionLapCount === next) return;
  store.navigationMissionLapCount = next;
  void store.invalidateNavigationMissionReview();
};

const confirmStart = (event: MouseEvent) =>
  confirm.require({
    group: "navigation-mission",
    target: event.currentTarget as HTMLElement,
    header: "Start navigation mission?",
    message:
      "Each leg will be replanned from live fused localization. The vehicle may drive forward or reverse and will stop if safety validation fails.",
    icon: "pi pi-exclamation-triangle",
    rejectProps: { label: "Keep reviewing", severity: "secondary" },
    acceptProps: { label: "Start mission", severity: "danger" },
    accept: () => void store.startNavigationMission(maxSpeed.value),
  });

const refreshRuntime = async () => {
  if (polling) return;
  polling = true;
  try {
    await store.refreshNavigationMissionRuntime();
  } finally {
    polling = false;
  }
};

onMounted(() => {
  void store.refreshNavigationMissionPlan();
  void refreshRuntime();
  timer = setInterval(() => void refreshRuntime(), 250);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>
