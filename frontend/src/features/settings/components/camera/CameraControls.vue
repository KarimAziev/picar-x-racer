<template>
  <div class="flex flex-col gap-3 min-w-0">
    <p v-if="loading" class="text-sm text-muted-color" role="status">
      Checking camera controls…
    </p>
    <p v-else-if="error" class="text-sm text-error" role="alert">{{ error }}</p>
    <p v-else-if="capabilities?.message" class="text-sm text-muted-color">
      {{ capabilities.message }}
    </p>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div class="flex flex-col gap-1 min-w-0">
        <label :for="`${id}-exposure`">Exposure</label>
        <Select
          :inputId="`${id}-exposure`"
          placeholder="Camera default"
          :modelValue="model.exposure_mode ?? null"
          :options="exposureOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full! max-w-none!"
          fluid
          :disabled="disabled || loading"
          @update:modelValue="setExposure"
        />
        <span
          v-if="capabilities && !capabilities.exposure_modes.length"
          class="text-sm text-muted-color"
          >Exposure controls unavailable.</span
        >
      </div>
      <div
        v-if="model.exposure_mode === 'manual'"
        class="flex flex-col gap-1 min-w-0"
      >
        <label :for="`${id}-exposure-time`">Exposure time (µs)</label>
        <InputNumber
          :inputId="`${id}-exposure-time`"
          :modelValue="model.exposure_time_us"
          @update:modelValue="model = { ...model, exposure_time_us: $event }"
          :min="capabilities?.exposure_time_us?.min ?? 1"
          :max="maxExposure"
          :step="capabilities?.exposure_time_us?.step ?? 1"
          :useGrouping="false"
          :maxFractionDigits="0"
          class="w-full! max-w-none!"
          inputClass="w-full! max-w-none!"
          fluid
          :disabled="disabled || loading"
        />
        <span class="text-sm text-muted-color"
          >1,000 µs = 1 ms. Maximum {{ maxExposure }} µs at this frame
          rate.</span
        >
      </div>
      <div class="flex flex-col gap-1 min-w-0">
        <label :for="`${id}-focus`">Focus</label>
        <Select
          :inputId="`${id}-focus`"
          placeholder="Camera default"
          :modelValue="model.focus_mode ?? null"
          :options="focusOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full! max-w-none!"
          fluid
          :disabled="disabled || loading"
          @update:modelValue="setFocus"
        />
        <span
          v-if="capabilities && !capabilities.focus_modes.length"
          class="text-sm text-muted-color"
          >Focus controls unavailable.</span
        >
      </div>
      <div
        v-if="model.focus_mode === 'manual'"
        class="flex flex-col gap-1 min-w-0"
      >
        <label :for="`${id}-focus-position`"
          >Focus position ({{
            capabilities?.focus_position?.unit ?? "camera units"
          }})</label
        >
        <InputNumber
          :inputId="`${id}-focus-position`"
          :modelValue="model.focus_position"
          @update:modelValue="model = { ...model, focus_position: $event }"
          :min="capabilities?.focus_position?.min"
          :max="capabilities?.focus_position?.max"
          :step="capabilities?.focus_position?.step ?? 0.1"
          :maxFractionDigits="3"
          :useGrouping="false"
          class="w-full! max-w-none!"
          inputClass="w-full! max-w-none!"
          fluid
          :disabled="disabled || loading"
        />
        <span
          v-if="capabilities?.focus_position?.unit === 'dioptres'"
          class="text-sm text-muted-color"
          >0 focuses at infinity; 1 at about 1 metre; 2 at about 0.5
          metres.</span
        >
      </div>
    </div>
    <p class="text-sm text-muted-color">
      Camera default leaves that control unchanged. Automatic focus adjusts
      continuously. Available controls depend on the camera.
    </p>
    <p v-if="!valid && !loading" class="text-sm text-error" role="alert">
      Choose supported modes and values within the camera limits. Exposure must
      fit the frame interval.
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { useCameraStore } from "@/features/settings/stores";
import type {
  CameraControls,
  CameraControlMode,
} from "@/features/settings/camera-controls";
import { validCameraControls } from "@/features/settings/camera-controls";

const props = defineProps<{
  id: string;
  device?: string | null;
  fps?: number | null;
  disabled?: boolean;
}>();
const model = defineModel<CameraControls>({ default: () => ({}) });
const store = useCameraStore();
const capabilities = computed(
  () => store.controlCapabilities[props.device ?? ""],
);
const loading = computed(() => store.controlsLoading[props.device ?? ""]);
const error = computed(() => store.controlErrors[props.device ?? ""]);
const valid = computed(() =>
  validCameraControls(model.value, capabilities.value, props.fps),
);
const options = (modes: CameraControlMode[]) => [
  { label: "Camera default", value: null },
  ...modes.map((value) => ({
    label: value === "auto" ? "Automatic" : "Manual",
    value,
  })),
];
const exposureOptions = computed(() =>
  options(capabilities.value?.exposure_modes ?? []),
);
const focusOptions = computed(() =>
  options(capabilities.value?.focus_modes ?? []),
);
const maxExposure = computed(() =>
  Math.floor(
    Math.min(
      capabilities.value?.exposure_time_us?.max ?? 1_000_000,
      1_000_000,
      props.fps ? 1_000_000 / props.fps : 1_000_000,
    ),
  ),
);
const setExposure = (mode: CameraControlMode | null) => {
  model.value = {
    ...model.value,
    exposure_mode: mode,
    exposure_time_us:
      mode === "manual"
        ? Math.ceil(capabilities.value?.exposure_time_us?.min ?? 1000)
        : null,
  };
};
const setFocus = (mode: CameraControlMode | null) => {
  model.value = {
    ...model.value,
    focus_mode: mode,
    focus_position:
      mode === "manual" ? (capabilities.value?.focus_position?.min ?? 0) : null,
  };
};
watch(
  () => props.device,
  (device) => {
    if (device) void store.fetchControlCapabilities(device);
  },
  { immediate: true },
);
</script>
