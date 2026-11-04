<template>
  <div class="space-y-4">
    <svg
      v-if="kind === 'body'"
      viewBox="0 0 560 210"
      role="img"
      aria-label="Top view: wheelbase runs between axle centres; rear overhang runs from rear axle to rear end"
      class="mx-auto w-full max-w-xl text-slate-500 dark:text-slate-300"
    >
      <rect
        x="110"
        y="60"
        width="330"
        height="100"
        rx="15"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      />
      <path
        d="M170 45V175 M375 45V175"
        stroke="currentColor"
        stroke-dasharray="5 4"
      />
      <path
        d="M170 30H375 M170 24V36 M375 24V36"
        stroke="#38bdf8"
        stroke-width="2"
      />
      <text
        x="272"
        y="20"
        fill="currentColor"
        text-anchor="middle"
        font-size="14"
      >
        Axle spacing (wheelbase)
      </text>
      <text
        x="272"
        y="115"
        fill="currentColor"
        text-anchor="middle"
        font-size="14"
      >
        Front →
      </text>
      <path
        d="M110 190H170 M110 184V196 M170 184V196"
        stroke="#38bdf8"
        stroke-width="2"
      />
      <text
        x="140"
        y="208"
        fill="currentColor"
        text-anchor="middle"
        font-size="12"
      >
        Rear overhang
      </text>
      <path
        d="M465 60V160 M459 60H471 M459 160H471"
        stroke="#38bdf8"
        stroke-width="2"
      />
      <text x="478" y="115" fill="currentColor" font-size="12">Width</text>
    </svg>
    <label v-if="kind === 'mounting'" class="block"
      >Sensor
      <select
        v-model="sensor"
        :disabled="reviewing || busy"
        class="measure-input"
        @change="loadMount"
      >
        <option value="lidar">LiDAR</option>
        <option value="imu">IMU</option>
      </select>
    </label>
    <div class="grid gap-4 sm:grid-cols-2">
      <label v-for="field in fields" :key="field.key" class="block text-sm">
        <span class="font-semibold">{{ field.label }}</span>
        <input
          v-model.number="values[field.key]"
          type="number"
          :step="field.step"
          :min="field.min"
          :max="field.max"
          :disabled="reviewing || busy"
          class="measure-input"
        />
        <span class="mt-1 block text-xs text-slate-500 dark:text-slate-400">{{
          field.help
        }}</span>
      </label>
    </div>
    <p v-if="error" role="alert" class="text-red-600 dark:text-red-300">
      {{ error }}
    </p>
    <div v-if="reviewing" class="rounded-lg border border-sky-500 p-4">
      <p class="font-semibold">Review these measurements</p>
      <ul class="mt-2 list-inside list-disc">
        <li v-for="field in fields" :key="field.key">
          {{ field.label }}: {{ values[field.key] }}
        </li>
      </ul>
      <p class="mt-2 text-sm">
        Save these values, then restart the robot application before driving.
        Sensors are not enabled by this step.
      </p>
    </div>
    <p
      v-if="saved"
      role="status"
      class="text-emerald-600 dark:text-emerald-300"
    >
      Measurements saved. Restart the robot application before driving with
      them.
    </p>
    <div class="flex gap-3">
      <button
        v-if="!reviewing"
        type="button"
        class="guide-primary"
        :disabled="busy"
        @click="review"
      >
        Review measurements
      </button>
      <template v-else>
        <button
          type="button"
          class="guide-secondary"
          :disabled="busy"
          @click="reviewing = false"
        >
          Edit measurements
        </button>
        <button
          type="button"
          class="guide-primary"
          :disabled="busy"
          @click="save"
        >
          {{ busy ? "Saving…" : "Apply measurements" }}
        </button>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { robotApi } from "@/api";
import { useRobotStore } from "@/features/settings/stores";
import type { Data } from "@/features/settings/stores/robot";
import { calibrationError } from "./session";
const props = defineProps<{ kind: "body" | "mounting" }>();
const store = useRobotStore();
const sensor = ref<"lidar" | "imu">("lidar");
const values = reactive<Record<string, number | null>>({
  wheelbase:
    store.data.ackermann_odometry.wheelbase_m === null
      ? null
      : store.data.ackermann_odometry.wheelbase_m * 100,
  length:
    store.data.navigation.body_length_m === null
      ? null
      : store.data.navigation.body_length_m * 100,
  width:
    store.data.navigation.body_width_m === null
      ? null
      : store.data.navigation.body_width_m * 100,
  rear:
    store.data.navigation.rear_overhang_m === null
      ? null
      : store.data.navigation.rear_overhang_m * 100,
});
function loadMount() {
  const transform = store.data.localization_sensors[sensor.value].transform;
  for (const axis of ["x_m", "y_m", "z_m"] as const)
    values[axis] = transform[axis] * 100;
  for (const axis of ["roll_rad", "pitch_rad", "yaw_rad"] as const)
    values[axis] = (transform[axis] * 180) / Math.PI;
}
loadMount();
const fields = computed(() =>
  props.kind === "body"
    ? [
        {
          key: "wheelbase",
          label: "Axle spacing (cm)",
          help: "Centre of rear axle to centre of front axle.",
          min: 1,
          max: 300,
          step: 0.1,
        },
        {
          key: "length",
          label: "Overall length (cm)",
          help: "Frontmost to rearmost point, including attached equipment.",
          min: 1,
          max: 300,
          step: 0.1,
        },
        {
          key: "width",
          label: "Overall width (cm)",
          help: "Include wheels. If asymmetric, double the larger distance from the centreline to either side.",
          min: 1,
          max: 300,
          step: 0.1,
        },
        {
          key: "rear",
          label: "Rear axle to rear end (cm)",
          help: "Measure backward from the rear axle centre to the rearmost point.",
          min: 0,
          max: 300,
          step: 0.1,
        },
      ]
    : [
        {
          key: "x_m",
          label: "Forward offset (cm)",
          help: "From the rear axle midpoint. Negative means behind the axle.",
          min: -300,
          max: 300,
          step: 0.1,
        },
        {
          key: "y_m",
          label: "Left offset (cm)",
          help: "From the chassis centreline. Negative means to the right.",
          min: -300,
          max: 300,
          step: 0.1,
        },
        {
          key: "z_m",
          label: "Height above rear axle (cm)",
          help: "From the rear axle centre to the sensor centre. Negative means below the axle.",
          min: -300,
          max: 300,
          step: 0.1,
        },
        {
          key: "roll_rad",
          label: "Sideways tilt (°)",
          help: "0° when level; positive when the sensor's left side is raised.",
          min: -180,
          max: 180,
          step: 1,
        },
        {
          key: "pitch_rad",
          label: "Forward tilt (°)",
          help: "0° when level; positive when the sensor's forward axis points down.",
          min: -180,
          max: 180,
          step: 1,
        },
        {
          key: "yaw_rad",
          label: "Direction offset (°)",
          help: "0° points forward, +90° left, −90° right, 180° backward.",
          min: -180,
          max: 180,
          step: 1,
        },
      ],
);
const reviewing = ref(false),
  busy = ref(false),
  error = ref(""),
  saved = ref(false);
function review() {
  error.value = "";
  saved.value = false;
  if (
    fields.value.some(
      (f) =>
        typeof values[f.key] !== "number" ||
        !Number.isFinite(values[f.key]) ||
        values[f.key]! < f.min ||
        values[f.key]! > f.max,
    )
  ) {
    error.value =
      "Enter a measurement in every field, within its displayed limits.";
    return;
  }
  if (
    props.kind === "body" &&
    values.rear! + values.wheelbase! >= values.length!
  ) {
    error.value =
      "Overall length must include the rear overhang, axle spacing and the front of the robot. Recheck these measurements.";
    return;
  }
  reviewing.value = true;
}
async function save() {
  busy.value = true;
  error.value = "";
  try {
    const update =
      props.kind === "body"
        ? {
            ackermann_odometry: { wheelbase_m: values.wheelbase! / 100 },
            navigation: {
              body_length_m: values.length! / 100,
              body_width_m: values.width! / 100,
              rear_overhang_m: values.rear! / 100,
            },
          }
        : {
            localization_sensors: {
              [sensor.value]: {
                transform: Object.fromEntries(
                  fields.value.map((f) => [
                    f.key,
                    values[f.key]! *
                      (f.key.endsWith("_m") ? 0.01 : Math.PI / 180),
                  ]),
                ),
              },
            },
          };
    await robotApi.patch("px/api/settings/config", update);
    store.data = await robotApi.get<Data>("px/api/settings/config");
    reviewing.value = false;
    saved.value = true;
  } catch (e) {
    error.value = calibrationError(e);
  } finally {
    busy.value = false;
  }
}
</script>
