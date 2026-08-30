<template>
  <section
    class="rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900"
  >
    <ConfirmPopup group="relative-motion" />
    <div class="flex items-start justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold">Relative motion</h2>
        <p class="text-[0.68rem] text-surface-500">
          Odometry-bounded straight or steering-arc action
        </p>
      </div>
      <Tag :severity="severity" :value="label" />
    </div>
    <ButtonGroup class="mt-3" aria-label="Relative motion type">
      <Button
        label="Straight"
        icon="pi pi-arrow-up"
        size="small"
        :outlined="actionType !== 'distance'"
        :severity="actionType === 'distance' ? 'primary' : 'secondary'"
        :aria-pressed="actionType === 'distance'"
        :disabled="running"
        @click="actionType = 'distance'"
      />
      <Button
        label="Steering arc"
        icon="pi pi-replay"
        size="small"
        :outlined="actionType !== 'arc'"
        :severity="actionType === 'arc' ? 'primary' : 'secondary'"
        :aria-pressed="actionType === 'arc'"
        :disabled="running"
        @click="actionType = 'arc'"
      />
    </ButtonGroup>
    <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
      <label
        >Distance (m)<InputNumber
          v-model="distance"
          class="mt-1"
          :min="-10"
          :max="10"
          :step="0.1"
          :max-fraction-digits="2"
          show-buttons
          fluid
          :disabled="running"
      /></label>
      <label
        >Speed (m/s)<InputNumber
          v-model="speed"
          class="mt-1"
          :min="0.04"
          :max="1"
          :step="0.05"
          :max-fraction-digits="2"
          show-buttons
          fluid
          :disabled="running"
      /></label>
      <label v-if="actionType === 'arc'" class="col-span-2"
        >Steering (°)<InputNumber
          v-model="steeringAngle"
          class="mt-1"
          :min="-maxSteeringAngle"
          :max="maxSteeringAngle"
          :step="1"
          :min-fraction-digits="0"
          :max-fraction-digits="1"
          show-buttons
          fluid
          :disabled="running"
      /></label>
    </div>
    <p v-if="actionType === 'arc'" class="mt-2 text-[0.68rem] text-surface-500">
      Steering is held at a fixed signed angle. The backend limits it to ±{{
        maxSteeringAngle.toFixed(1)
      }}° and verifies measured yaw before declaring success.
    </p>
    <div
      v-if="distance < 0"
      class="mt-2 rounded bg-amber-50 p-2 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-100"
    >
      Reverse uses odometry only. A front-facing LiDAR does not protect the rear
      path.
    </div>
    <div class="mt-3">
      <Button
        v-if="!running"
        label="Review and start"
        icon="pi pi-compass"
        size="small"
        :disabled="!canStart"
        :loading="store.relativeMotionLoading"
        @click="confirmStart"
      />
      <Button
        v-else
        label="Cancel action"
        icon="pi pi-stop"
        severity="danger"
        size="small"
        :loading="store.relativeMotionLoading"
        @click="store.cancelRelativeMotion()"
      />
    </div>
    <div v-if="status?.action_id" class="mt-3 text-xs">
      <div v-if="status.action_type" class="mb-1 text-surface-500">
        {{ status.action_type === "arc" ? "Steering arc" : "Straight drive" }}
        <span
          v-if="
            status.action_type === 'arc' && status.steering_angle_deg !== null
          "
        >
          · {{ formatSigned(status.steering_angle_deg) }}° steering
        </span>
      </div>
      <div class="flex justify-between">
        <span>{{ status.progress_m.toFixed(2) }} m traveled</span
        ><span v-if="status.remaining_m !== null"
          >{{ status.remaining_m.toFixed(2) }} m left</span
        >
      </div>
      <ProgressBar class="mt-1 h-2" :value="progress" :show-value="false" />
      <div
        v-if="status.target_yaw_rad !== null"
        class="mt-2 flex justify-between text-surface-500"
      >
        <span
          >Yaw
          {{
            formatSigned(radiansToDegrees(status.yaw_progress_rad ?? 0))
          }}°</span
        >
        <span
          >target
          {{ formatSigned(radiansToDegrees(status.target_yaw_rad)) }}°</span
        >
      </div>
      <div
        v-if="status.reason"
        class="mt-2 rounded bg-surface-100 p-2 dark:bg-surface-800"
      >
        {{ status.reason }}
      </div>
    </div>
    <div v-if="store.relativeMotionError" class="mt-2 text-xs text-red-500">
      {{ store.relativeMotionError }}
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import ConfirmPopup from "primevue/confirmpopup";
import { useConfirm } from "primevue/useconfirm";
import { type RelativeActionType, useAutonomyStore } from "@/features/autonomy";

const store = useAutonomyStore();
const confirm = useConfirm();
const distance = ref(0.5);
const speed = ref(0.15);
const steeringAngle = ref(15);
const actionType = ref<RelativeActionType>("distance");
let timer: ReturnType<typeof setInterval> | null = null;
const status = computed(() => store.relativeMotion);
const running = computed(() => status.value?.state === "running");
const maxSteeringAngle = computed(
  () => status.value?.max_abs_steering_angle_deg ?? 60,
);
const canStart = computed(
  () =>
    status.value?.available &&
    Math.abs(distance.value) >= 0.01 &&
    speed.value > 0 &&
    (actionType.value === "distance" ||
      (Math.abs(steeringAngle.value) >= 1 &&
        Math.abs(steeringAngle.value) <= maxSteeringAngle.value)) &&
    !store.relativeMotionLoading,
);
const label = computed(() =>
  status.value?.available === false
    ? "Unavailable"
    : `Action: ${status.value?.state ?? "checking"}`,
);
const severity = computed(() =>
  running.value || status.value?.state === "succeeded"
    ? "success"
    : ["failed", "blocked"].includes(status.value?.state ?? "")
      ? "danger"
      : "secondary",
);
const progress = computed(() =>
  Math.min(
    100,
    status.value?.distance_m
      ? (status.value.progress_m / Math.abs(status.value.distance_m)) * 100
      : 0,
  ),
);
const radiansToDegrees = (radians: number) => (radians * 180) / Math.PI;
const formatSigned = (value: number) =>
  (value > 0 ? "+" : "") + value.toFixed(1);
const startAction = () => {
  if (actionType.value === "arc") {
    void store.startRelativeArc(
      distance.value,
      speed.value,
      steeringAngle.value,
    );
    return;
  }
  void store.startRelativeDistance(distance.value, speed.value);
};
const confirmStart = (event: MouseEvent) =>
  confirm.require({
    group: "relative-motion",
    target: event.currentTarget as HTMLElement,
    icon: "pi pi-compass",
    message:
      "Enter autonomous mode and drive " +
      Math.abs(distance.value).toFixed(2) +
      " m " +
      (distance.value > 0 ? "forward" : "reverse") +
      (actionType.value === "arc"
        ? " with " + formatSigned(steeringAngle.value) + "° steering"
        : " in a straight line") +
      " at up to " +
      speed.value.toFixed(2) +
      " m/s?",
    rejectProps: { label: "Cancel", severity: "secondary", outlined: true },
    acceptProps: { label: "Start action", severity: "danger" },
    accept: startAction,
  });
onMounted(() => {
  void store.refreshRelativeMotion();
  timer = setInterval(() => void store.refreshRelativeMotion(), 250);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>
