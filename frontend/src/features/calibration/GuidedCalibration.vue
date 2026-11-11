<template>
  <section
    id="guided-calibration"
    class="guided-calibration mb-5 rounded-xl border border-sky-500/40 bg-sky-50/50 p-4 dark:bg-slate-900 sm:p-6"
    aria-label="Guided motion calibration"
  >
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold">Measure robot motion & geometry</h2>
        <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Measure body geometry, wheel travel, steering response, and sensors
          step by step. Review each result before saving it.
        </p>
      </div>
      <button
        v-if="guide && !sessionId"
        type="button"
        class="guide-secondary"
        :disabled="busy"
        @click="choose(null)"
      >
        All guides
      </button>
    </div>
    <div class="mt-5" aria-live="polite">
      <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
        <p class="font-semibold">
          {{ completedCount }} of {{ guides.length }} guides completed
        </p>
        <p class="text-slate-600 dark:text-slate-300">
          Progress is saved with the robot settings.
        </p>
      </div>
      <div
        class="mt-2 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
        role="progressbar"
        aria-label="Completed calibration guides"
        :aria-valuenow="completedCount"
        :aria-valuemin="0"
        :aria-valuemax="guides.length"
      >
        <div
          class="h-full rounded-full bg-emerald-600 transition-all dark:bg-emerald-400"
          :style="{ width: `${(completedCount / guides.length) * 100}%` }"
        />
      </div>
    </div>
    <div v-if="!guide" class="mt-5 grid gap-3 sm:grid-cols-2">
      <button
        v-for="(item, index) in guideCards"
        :key="item.kind"
        type="button"
        class="flex flex-col rounded-lg border p-4 text-left hover:border-sky-500 focus-visible:outline-2 focus-visible:outline-sky-500"
        :class="
          item.progress.state === 'complete'
            ? 'border-emerald-500/60 bg-emerald-50/60 dark:bg-emerald-950/25'
            : 'border-slate-300 dark:border-slate-600'
        "
        :data-guide="item.kind"
        @click="choose(item.kind)"
      >
        <span class="flex w-full flex-wrap items-center justify-between gap-2">
          <span class="text-xs text-sky-600 dark:text-sky-300"
            >{{ index + 1 }} / {{ guides.length }}</span
          >
          <span
            class="inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-semibold"
            :class="progressClass(item.progress.state)"
          >
            <i
              :class="
                item.progress.state === 'complete'
                  ? 'pi pi-check-circle'
                  : item.progress.state === 'todo'
                    ? 'pi pi-circle'
                    : 'pi pi-clock'
              "
              aria-hidden="true"
            />
            {{ item.progress.label }}
          </span>
        </span>
        <span class="mt-1 block font-semibold">{{ item.title }}</span
        ><span class="mt-1 block text-sm text-slate-600 dark:text-slate-300">{{
          item.description
        }}</span>
        <span
          class="mt-auto block pt-3 text-xs text-slate-600 dark:text-slate-300"
          >{{ item.progress.detail }}</span
        >
      </button>
    </div>
    <template v-else>
      <h3 class="mt-5 text-lg font-semibold">{{ guide.title }}</h3>
      <p
        v-if="activeProgress"
        class="mt-2 text-sm"
        :class="
          activeProgress.state === 'complete'
            ? 'text-emerald-700 dark:text-emerald-300'
            : 'text-slate-600 dark:text-slate-300'
        "
      >
        <i
          v-if="activeProgress.state === 'complete'"
          class="pi pi-check-circle mr-1"
          aria-hidden="true"
        />
        {{ activeProgress.label }} — {{ activeProgress.detail }}
      </p>
      <ol
        v-if="kind !== 'body' && kind !== 'mounting'"
        class="my-4 flex gap-4 border-b border-slate-400/30 pb-3 text-sm"
        aria-label="Calibration progress"
      >
        <li
          v-for="(label, index) in ['Prepare', 'Measure', 'Review']"
          :key="label"
          :aria-current="phase === index ? 'step' : undefined"
          :class="
            phase === index
              ? 'font-semibold text-sky-600 dark:text-sky-300'
              : 'text-slate-500'
          "
        >
          {{ index + 1 }}. {{ label }}
        </li>
      </ol>
      <p
        v-if="kind !== 'body' && kind !== 'mounting'"
        class="my-4 text-sm leading-relaxed"
      >
        {{ guide.steps[phase] }}
      </p>
      <ol v-else class="my-4 space-y-3">
        <li
          v-for="(instruction, index) in guide.steps"
          :key="instruction"
          class="flex gap-3 text-sm leading-relaxed"
        >
          <span class="font-semibold text-sky-600 dark:text-sky-300"
            >{{ index + 1 }}.</span
          ><span>{{ instruction }}</span>
        </li>
      </ol>
      <ManualMeasurements
        v-if="kind === 'body' || kind === 'mounting'"
        :key="kind"
        :kind="kind"
      />
      <template v-else>
        <button
          type="button"
          class="mb-4 text-sm underline underline-offset-4"
          :disabled="!!sessionId"
          @click="$emit('open-section', 'localization_sensors')"
        >
          Open sensor connections in Advanced settings
        </button>
        <div
          v-if="status"
          class="mb-4 grid grid-cols-2 gap-3 rounded-lg bg-white/60 p-3 text-sm dark:bg-slate-800"
          aria-label="Live measurements"
        >
          <p v-if="kind === 'wheel_distance' || powered">
            Wheel count
            <strong class="block">{{
              reading(status.encoder_ticks, 0, "counts")
            }}</strong>
          </p>
          <p v-if="powered">
            Wall distance
            <strong class="block">{{
              reading(status.wall_distance_m, 2, "m")
            }}</strong>
          </p>
          <p v-if="kind === 'imu_bias'">
            Rotation reading
            <strong class="block">{{
              reading(status.gyro_radps, 4, "rad/s")
            }}</strong>
          </p>
          <p v-if="steering">
            Steering sensor
            <strong class="block">{{
              reading(status.sensor_angle_deg, 1, "°")
            }}</strong>
          </p>
          <p v-if="sessionId">
            Recording time
            <strong class="block">{{ status.elapsed_s.toFixed(1) }} s</strong>
          </p>
        </div>
        <div
          v-if="phase === 0 && !sessionId && status?.blockers.length"
          class="mb-4 rounded-lg border border-amber-500/50 p-3 text-sm"
        >
          <p class="font-semibold">Before this guide can record</p>
          <ul class="mt-2 list-inside list-disc space-y-1">
            <li v-for="blocker in status.blockers" :key="blocker">
              {{ blocker }}
            </li>
          </ul>
        </div>
        <p v-if="status?.active && !sessionId" class="mb-3 text-sm">
          Another calibration is active. Finish it in the window that started
          it, or wait for its connection to expire.
        </p>
        <div class="grid gap-4 sm:grid-cols-2">
          <label
            v-if="kind === 'wheel_distance' && phase !== 2"
            class="text-sm font-semibold"
            >Distance between floor marks (cm)<input
              v-model.number="distanceCm"
              :disabled="!!sessionId"
              type="number"
              min="20"
              max="1000"
              step="1"
              class="measure-input"
            /><span class="mt-1 block text-xs font-normal"
              >Measure with a tape. Use the same rear-axle reference at both
              ends.</span
            ></label
          >
          <template v-if="powered && phase !== 2">
            <label class="text-sm font-semibold"
              >Driving direction<select
                v-model="direction"
                :disabled="!!sessionId"
                class="measure-input"
              >
                <option value="forward">Forward, toward wall</option>
                <option value="reverse">Reverse, away from wall</option>
              </select></label
            >
            <label class="text-sm font-semibold"
              >Motor power (%)<input
                v-model.number="power"
                :disabled="!!sessionId"
                type="number"
                min="5"
                :max="status?.max_power_percent ?? 20"
                step="5"
                class="measure-input"
              /><span class="mt-1 block text-xs font-normal"
                >Up to {{ status?.max_power_percent ?? 20 }}% unlocked. This is
                power, not measured speed.</span
              ></label
            >
            <label class="text-sm font-semibold"
              >Stop boundary from rear axle (cm)<input
                v-model.number="stopCm"
                :disabled="!!sessionId"
                type="number"
                min="20"
                max="500"
                step="5"
                class="measure-input"
              /><span class="mt-1 block text-xs font-normal"
                >Must extend beyond the body in the driving direction, with room
                to coast to a stop. Reaching it ends the trial.</span
              ></label
            >
            <label class="text-sm font-semibold"
              >Maximum drive time (s)<input
                v-model.number="duration"
                :disabled="!!sessionId"
                type="number"
                min="2"
                max="15"
                step="1"
                class="measure-input"
              /><span class="mt-1 block text-xs font-normal"
                >Release earlier to record a successful trial.</span
              ></label
            >
          </template>
          <label v-if="steering && sessionId" class="text-sm font-semibold"
            >Steering command (°)<input
              v-model.number="steeringDegrees"
              type="number"
              :min="servoMin"
              :max="servoMax"
              step="1"
              class="measure-input"
            /><span class="mt-1 block text-xs font-normal"
              >Move in small steps. Stay within the linkage's safe travel.</span
            ></label
          >
          <label
            v-if="kind === 'steering_range' && phase !== 2"
            class="text-sm font-semibold"
            >Measured wheel angle (°)<input
              v-model.number="wheelAngle"
              type="number"
              min="-45"
              max="45"
              step="0.5"
              class="measure-input"
            /><span class="mt-1 block text-xs font-normal"
              >Use a protractor. Negative is left; positive is right.</span
            ></label
          >
        </div>
        <label
          v-if="phase === 0 && !sessionId"
          class="my-4 flex items-start gap-2 text-sm"
          ><input v-model="ready" type="checkbox" class="mt-1" /><span>{{
            powered
              ? "The robot is on a level floor, the path is clear, and I am ready to stop it."
              : steering
                ? "The front wheels are raised, the linkage is clear, and I am ready to adjust steering."
                : "The robot and measuring area are ready. I have read the steps above."
          }}</span></label
        >
        <p
          v-if="error"
          role="alert"
          class="my-3 text-sm text-red-600 dark:text-red-300"
        >
          {{ error }}
        </p>
        <p
          v-if="message"
          role="status"
          class="my-3 text-sm text-emerald-700 dark:text-emerald-300"
        >
          {{ message }}
        </p>
        <div class="my-4 flex flex-wrap gap-3">
          <button
            v-if="phase === 0 && !sessionId"
            type="button"
            class="guide-primary"
            :disabled="
              busy ||
              !ready ||
              !status ||
              !!status.blockers.length ||
              status.active
            "
            @click="start"
          >
            Start trial
          </button>
          <template v-else-if="sessionId">
            <button
              v-if="powered"
              type="button"
              class="rounded-lg bg-amber-400 px-5 py-3 font-semibold text-slate-950 disabled:opacity-50"
              style="touch-action: none; user-select: none"
              :disabled="busy || released"
              @pointerdown.prevent="holdPointer"
              @pointerup.prevent="releaseDrive"
              @pointercancel="releaseDrive"
              @lostpointercapture="releaseDrive"
              @keydown.space.prevent="holdKey"
              @keyup.space.prevent="releaseDrive"
              @keydown.enter.prevent="holdKey"
              @keyup.enter.prevent="releaseDrive"
              @blur="releaseDrive"
            >
              {{
                driving
                  ? "Release to stop"
                  : released
                    ? "Movement complete"
                    : "Hold to drive"
              }}
            </button>
            <button
              type="button"
              class="guide-primary"
              :disabled="busy || driving || (powered && !released)"
              @click="finish"
            >
              Record trial
            </button>
            <button
              type="button"
              class="guide-secondary"
              :disabled="busy"
              @click="cancel"
            >
              Cancel and stop
            </button>
          </template>
        </div>
        <p
          v-if="sessionId && powered"
          class="text-xs text-slate-500 dark:text-slate-400"
        >
          Keep this window focused. Releasing Drive stops the motors. Losing the
          hold connection stops a powered trial after 350 ms, plus control-loop
          and hardware response time.
        </p>
        <button
          v-if="phase === 2 && !sessionId"
          type="button"
          class="guide-secondary mt-2"
          :disabled="busy"
          @click="
            phase = 0;
            ready = false;
            proposal = null;
            error = '';
            message = '';
          "
        >
          Prepare another trial
        </button>
        <div
          v-if="trials.length"
          class="mt-6 border-t border-slate-300 pt-4 dark:border-slate-600"
        >
          <h4 class="font-semibold">Recorded trials</h4>
          <p class="mt-1 text-sm">
            Select the accepted trials to compare and apply. Trials are kept
            until the robot application restarts.
          </p>
          <ul class="mt-3 space-y-3">
            <li
              v-for="trial in trials"
              :key="trial.id"
              class="rounded-lg border border-slate-300 p-3 text-sm dark:border-slate-600"
            >
              <label class="flex items-start gap-3"
                ><input
                  v-model="selected"
                  :value="trial.id"
                  :disabled="!trial.accepted || !!sessionId || busy"
                  type="checkbox"
                  class="mt-1"
                /><span
                  ><strong>{{
                    trial.accepted ? "Accepted" : "Repeat needed"
                  }}</strong
                  ><span class="mt-1 block">{{
                    trialSummary(trial)
                  }}</span></span
                ></label
              >
            </li>
          </ul>
          <button
            type="button"
            class="guide-primary mt-4"
            :disabled="busy || !!sessionId || !selected.length"
            @click="preview"
          >
            Review selected trials
          </button>
        </div>
        <div v-if="proposal" class="mt-4 rounded-lg border border-sky-500 p-4">
          <h4 class="font-semibold">Measurements to save</h4>
          <ul class="my-3 list-inside list-disc space-y-1 text-sm">
            <li v-for="line in reviewLines(proposal)" :key="line">
              {{ line }}
            </li>
          </ul>
          <p class="mb-3 text-sm">
            Applying saves these measurements. Restart the robot application
            before driving. Features remain switched off until you enable them
            in the mapping setup.
          </p>
          <button
            type="button"
            class="guide-primary"
            :disabled="busy || !!sessionId"
            @click="apply"
          >
            Apply calibration
          </button>
        </div>
      </template>
    </template>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { robotApi } from "@/api";
import { useRobotStore } from "@/features/settings/stores";
import type { Data } from "@/features/settings/stores/robot";
import ManualMeasurements from "@/features/calibration/ManualMeasurements.vue";
import {
  guideProgress,
  type GuideState,
} from "@/features/calibration/progress";
import {
  guides,
  reviewLines,
  trialSummary,
  type GuideKind,
} from "@/features/calibration/guides";
import {
  CalibrationLease,
  calibrationError,
  calibrationPath,
  type CalibrationStatus,
} from "@/features/calibration/session";
defineEmits<{ "open-section": [section: string] }>();
const props = defineProps<{ suspended?: boolean }>();
const store = useRobotStore();
const phase = ref(0);
const kind = ref<GuideKind | null>(null),
  status = ref<CalibrationStatus | null>(null);
const guide = computed(() => guides.find((g) => g.kind === kind.value));
const guideCards = computed(() =>
  guides.map((item) => ({
    ...item,
    progress: guideProgress(store.data, item.kind),
  })),
);
const completedCount = computed(
  () =>
    guideCards.value.filter((item) => item.progress.state === "complete")
      .length,
);
const activeProgress = computed(
  () => guideCards.value.find((item) => item.kind === kind.value)?.progress,
);
const progressClass = (state: GuideState) =>
  state === "complete"
    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200"
    : state === "todo"
      ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
      : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200";
const powered = computed(
  () => kind.value === "speed" || kind.value === "stopping",
);
const steering = computed(
  () => kind.value === "steering_center" || kind.value === "steering_range",
);
const servoMin = computed(() =>
  Math.max(-45, store.data.steering_servo.min_angle),
);
const servoMax = computed(() =>
  Math.min(45, store.data.steering_servo.max_angle),
);
const distanceCm = ref(100),
  stopCm = ref(60),
  duration = ref(8),
  power = ref(20),
  wheelAngle = ref(0),
  steeringDegrees = ref(0);
const direction = ref<"forward" | "reverse">("forward");
const ready = ref(false),
  busy = ref(false),
  error = ref(""),
  message = ref(""),
  driving = ref(false),
  released = ref(false);
const sessionId = ref<string | null>(null),
  selected = ref<string[]>([]),
  proposal = ref<Record<string, any> | null>(null);
const trials = computed(() =>
  (status.value?.trials ?? []).filter((t) => t.kind === kind.value),
);
let lease: CalibrationLease | null = null,
  timer: ReturnType<typeof setInterval> | undefined,
  mounted = true;
const reading = (value: number | null, digits: number, unit: string) =>
  value === null ? "Waiting for sensor…" : `${value.toFixed(digits)} ${unit}`;
function choose(value: GuideKind | null) {
  phase.value = 0;
  kind.value = value;
  status.value = null;
  selected.value = [];
  proposal.value = null;
  error.value = "";
  message.value = "";
  ready.value = false;
  void poll();
}
async function poll() {
  const requestedKind = kind.value;
  if (
    !requestedKind ||
    requestedKind === "body" ||
    requestedKind === "mounting" ||
    sessionId.value ||
    busy.value
  )
    return;
  try {
    const result = await robotApi.get<CalibrationStatus>(
      `${calibrationPath}/status`,
      {
        params: {
          kind: requestedKind,
          direction: direction.value,
          stop_distance_m: Math.max(
            0.2,
            Math.min(5, Number(stopCm.value) / 100 || 0.6),
          ),
        },
      },
    );
    if (
      mounted &&
      kind.value === requestedKind &&
      !sessionId.value &&
      !busy.value
    )
      status.value = result;
  } catch (e) {
    if (mounted && kind.value === requestedKind && !sessionId.value) {
      status.value = null;
      error.value = calibrationError(e);
    }
  }
}
function receive(result: CalibrationStatus) {
  if (!mounted) return;
  status.value = result;
  if (!result.active) {
    if (sessionId.value) phase.value = 2;
    lease?.close();
    lease = null;
    sessionId.value = null;
    driving.value = false;
    ready.value = false;
  }
}
async function start() {
  busy.value = true;
  error.value = "";
  message.value = "";
  proposal.value = null;
  try {
    const result = await robotApi.post<CalibrationStatus>(
      `${calibrationPath}/start`,
      {
        kind: kind.value,
        direction: direction.value,
        power_percent: power.value,
        stop_distance_m: stopCm.value / 100,
        max_duration_s: duration.value,
        clear_path_confirmed: ready.value,
      },
    );
    if (!result.session_id) throw new Error("Missing session");
    if (!mounted || document.hidden || props.suspended) {
      await robotApi.post(`${calibrationPath}/${result.session_id}/cancel`);
      return;
    }
    sessionId.value = result.session_id;
    phase.value = 1;
    released.value = false;
    steeringDegrees.value = 0;
    lease = new CalibrationLease(result.session_id, receive, (reason) => {
      error.value = reason;
      lease = null;
      sessionId.value = null;
      driving.value = false;
      ready.value = false;
      void poll();
    });
    receive(result);
    await lease.heartbeat();
  } catch (e) {
    error.value = calibrationError(e);
  } finally {
    busy.value = false;
  }
}
function holdPointer(event: PointerEvent) {
  if (event.button !== 0 || driving.value || released.value) return;
  (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  driving.value = true;
  lease?.hold();
}
function holdKey(event: KeyboardEvent) {
  if (event.repeat || driving.value || released.value) return;
  driving.value = true;
  lease?.hold();
}
async function releaseDrive() {
  if (!driving.value) return;
  driving.value = false;
  released.value = true;
  await lease?.release();
}
async function finish() {
  if (!sessionId.value || driving.value) return;
  busy.value = true;
  error.value = "";
  const id = sessionId.value;
  lease?.close();
  lease = null;
  try {
    const result = await robotApi.post<CalibrationStatus>(
      `${calibrationPath}/${id}/finish`,
      {
        measured_distance_m:
          kind.value === "wheel_distance" ? distanceCm.value / 100 : null,
        measured_wheel_angle_deg:
          kind.value === "steering_range" ? wheelAngle.value : null,
      },
    );
    receive(result);
    phase.value = 2;
    const trial = result.trials.find((t) => t.id === id);
    if (trial?.accepted) {
      selected.value.push(id);
      message.value = trial.reason;
    } else error.value = trial?.reason ?? "The trial could not be recorded.";
  } catch (e) {
    error.value = calibrationError(e);
    void robotApi.post(`${calibrationPath}/${id}/cancel`).catch(() => {});
    sessionId.value = null;
  } finally {
    busy.value = false;
    ready.value = false;
  }
}
async function cancel() {
  const id = sessionId.value;
  lease?.close();
  lease = null;
  driving.value = false;
  sessionId.value = null;
  ready.value = false;
  phase.value = 0;
  if (!id) return;
  busy.value = true;
  try {
    receive(
      await robotApi.post<CalibrationStatus>(`${calibrationPath}/${id}/cancel`),
    );
  } catch (e) {
    error.value = calibrationError(e);
  } finally {
    busy.value = false;
  }
}
async function preview() {
  busy.value = true;
  error.value = "";
  proposal.value = null;
  try {
    proposal.value = await robotApi.post(`${calibrationPath}/preview`, {
      trial_ids: selected.value,
    });
  } catch (e) {
    error.value = calibrationError(e);
  } finally {
    busy.value = false;
  }
}
async function apply() {
  busy.value = true;
  error.value = "";
  try {
    receive(
      await robotApi.post<CalibrationStatus>(`${calibrationPath}/apply`, {
        trial_ids: selected.value,
      }),
    );
    store.data = await robotApi.get<Data>("px/api/settings/config");
    proposal.value = null;
    selected.value = [];
    message.value =
      "Calibration saved. Restart the robot application before driving with these measurements.";
  } catch (e) {
    error.value = calibrationError(e);
  } finally {
    busy.value = false;
  }
}
function loseFocus() {
  if (sessionId.value) {
    error.value =
      "The trial was cancelled because this window lost focus. Prepare the robot and start again.";
    void cancel();
  }
}
watch(
  () => props.suspended,
  (suspended) => {
    if (suspended) void cancel();
  },
);
function visibilityChanged() {
  if (document.hidden) loseFocus();
}
watch(
  selected,
  () => {
    proposal.value = null;
  },
  { deep: true },
);
watch(steeringDegrees, (value) => {
  if (
    lease &&
    Number.isFinite(value) &&
    value >= servoMin.value &&
    value <= servoMax.value
  )
    lease.steeringDegrees = value;
});
onMounted(() => {
  timer = setInterval(() => {
    if (lease) void lease.heartbeat();
  }, 100);
  window.addEventListener("blur", loseFocus);
  document.addEventListener("visibilitychange", visibilityChanged);
});
let pollTimer = setInterval(() => {
  void poll();
}, 1000);
onUnmounted(() => {
  mounted = false;
  clearInterval(timer);
  clearInterval(pollTimer);
  window.removeEventListener("blur", loseFocus);
  document.removeEventListener("visibilitychange", visibilityChanged);
  void cancel();
});
</script>
<style>
.guided-calibration {
  font-size: 16px;
  line-height: 1.5;
}
.guided-calibration .text-sm {
  font-size: 14px;
}
.guided-calibration .text-xs {
  font-size: 12px;
}
.guided-calibration .text-lg {
  font-size: 20px;
}
#guided-calibration input.measure-input,
#guided-calibration select.measure-input {
  width: 100%;
  min-height: 44px;
  height: auto;
  font-size: 16px;
}
#guided-calibration input[type="checkbox"] {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
}
#guided-calibration button {
  min-height: 40px;
}

.guided-calibration .measure-input {
  display: block;
  width: 100%;
  margin-top: 0.4rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid #64748b;
  border-radius: 0.5rem;
  background: transparent;
  font-weight: 400;
}
.guided-calibration .measure-input option {
  color: #0f172a;
  background: #f8fafc;
}
.guided-calibration .guide-primary,
.guided-calibration .guide-secondary {
  border-radius: 0.5rem;
  padding: 0.6rem 1rem;
  font-size: 14px;
  font-weight: 600;
}
.guided-calibration .guide-primary {
  background: #0369a1;
  color: white;
}
.guided-calibration .guide-secondary {
  border: 1px solid #64748b;
}
.guided-calibration button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.guided-calibration input:focus-visible,
.guided-calibration button:focus-visible,
.guided-calibration select:focus-visible {
  outline: 2px solid #38bdf8;
  outline-offset: 3px;
}
</style>
