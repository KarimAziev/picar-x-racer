<template>
  <section
    class="rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900"
  >
    <ConfirmPopup group="mapping-session" />
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold">Mapping session</h2>
        <p class="text-[0.68rem] text-surface-500 dark:text-surface-400">
          Scan insertion only; these controls never move the vehicle
        </p>
      </div>
      <Tag :severity="stateSeverity" :value="stateLabel" />
    </div>

    <div
      v-if="store.mappingActionError"
      class="mt-2 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-950 dark:text-red-200"
    >
      {{ store.mappingActionError }}
    </div>

    <div class="mt-3 flex flex-wrap gap-2">
      <Button
        :label="session?.state === 'paused' ? 'Resume' : 'Start'"
        icon="pi pi-play"
        size="small"
        :disabled="!canStart"
        :loading="store.mappingActionLoading && pendingAction === 'start'"
        @click="run('start')"
      />
      <Button
        label="Pause"
        icon="pi pi-pause"
        severity="secondary"
        size="small"
        :disabled="session?.state !== 'active' || store.mappingActionLoading"
        :loading="store.mappingActionLoading && pendingAction === 'pause'"
        @click="run('pause')"
      />
      <Button
        label="Finish"
        icon="pi pi-check"
        severity="secondary"
        size="small"
        outlined
        :disabled="
          !['active', 'paused'].includes(session?.state ?? '') ||
          store.mappingActionLoading
        "
        :loading="store.mappingActionLoading && pendingAction === 'finish'"
        @click="run('finish')"
      />
      <Button
        label="Clear"
        icon="pi pi-eraser"
        severity="warning"
        size="small"
        outlined
        :disabled="!session?.enabled || store.mappingActionLoading"
        @click="confirmDestructive($event, 'clear')"
      />
      <Button
        label="Reset"
        icon="pi pi-refresh"
        severity="danger"
        size="small"
        outlined
        :disabled="!session?.enabled || store.mappingActionLoading"
        @click="confirmDestructive($event, 'reset')"
      />
    </div>

    <dl
      v-if="session?.enabled"
      class="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-xs sm:grid-cols-3 xl:grid-cols-2"
    >
      <div>
        <dt class="text-surface-500">Session</dt>
        <dd>#{{ session.session_id || "—" }}</dd>
      </div>
      <div>
        <dt class="text-surface-500">Map updates</dt>
        <dd>{{ session.map_sequence.toLocaleString() }}</dd>
      </div>
      <div>
        <dt class="text-surface-500">Scans inserted</dt>
        <dd>{{ session.scans_inserted.toLocaleString() }}</dd>
      </div>
      <div>
        <dt class="text-surface-500">Returns inserted</dt>
        <dd>{{ session.returns_inserted.toLocaleString() }}</dd>
      </div>
      <div>
        <dt class="text-surface-500">Pose source</dt>
        <dd>{{ poseSourceLabel }}</dd>
      </div>
      <div v-if="session.scans_inserted_with_localization">
        <dt class="text-surface-500">Fused scans</dt>
        <dd>
          {{ session.scans_inserted_with_localization.toLocaleString() }}
        </dd>
      </div>
      <div v-if="session.localization_fallbacks">
        <dt class="text-amber-600">Raw fallbacks</dt>
        <dd>{{ session.localization_fallbacks.toLocaleString() }}</dd>
      </div>
      <div v-if="session.rejected_missing_odometry">
        <dt class="text-amber-600">Missing pose</dt>
        <dd>{{ session.rejected_missing_odometry.toLocaleString() }}</dd>
      </div>
      <div v-if="session.rejected_stale_odometry">
        <dt class="text-amber-600">Stale pose</dt>
        <dd>{{ session.rejected_stale_odometry.toLocaleString() }}</dd>
      </div>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import ConfirmPopup from "primevue/confirmpopup";
import { useConfirm } from "primevue/useconfirm";
import {
  useAutonomyStore,
  type MappingSessionAction,
} from "@/features/autonomy";

const store = useAutonomyStore();
const confirm = useConfirm();
const pendingAction = ref<MappingSessionAction | null>(null);
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const session = computed(() => store.mappingSession);
const canStart = computed(
  () =>
    Boolean(session.value?.enabled) &&
    session.value?.state !== "active" &&
    !store.mappingActionLoading,
);
const stateLabel = computed(() => {
  if (!session.value) return "Checking…";
  if (!session.value.enabled) return "Disabled";
  return `Map: ${session.value.state}`;
});
const stateSeverity = computed(() => {
  if (session.value?.state === "active") return "success";
  if (session.value?.state === "paused") return "warning";
  return "secondary";
});
const poseSourceLabel = computed(() => {
  if (!session.value) return "—";
  if (session.value.active_pose_source === "localization") {
    return "Fused localization";
  }
  if (
    session.value.preferred_pose_source === "localization" &&
    session.value.active_pose_source === "odometry"
  ) {
    return "Raw odometry fallback";
  }
  if (session.value.active_pose_source === "odometry") return "Raw odometry";
  return session.value.preferred_pose_source === "localization"
    ? "Awaiting fused localization"
    : "Awaiting raw odometry";
});

const run = async (action: MappingSessionAction) => {
  pendingAction.value = action;
  await store.runMappingAction(action);
  pendingAction.value = null;
};

const confirmDestructive = (event: MouseEvent, action: "clear" | "reset") => {
  const reset = action === "reset";
  confirm.require({
    group: "mapping-session",
    target: event.currentTarget as HTMLElement,
    icon: reset ? "pi pi-refresh" : "pi pi-eraser",
    message: reset
      ? "Clear the map and return the session to idle? Fresh synchronized inputs will be required when it restarts."
      : "Clear every map cell while preserving the current session state?",
    rejectProps: {
      label: "Cancel",
      severity: "secondary",
      outlined: true,
    },
    acceptProps: {
      label: reset ? "Reset mapping" : "Clear map",
      severity: "danger",
    },
    accept: () => void run(action),
  });
};

onMounted(() => {
  void store.refreshMappingSession();
  refreshTimer = setInterval(() => void store.refreshMappingSession(), 2500);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>
