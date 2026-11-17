<template>
  <div class="flex flex-col gap-3 min-w-0">
    <label for="photo-preset" class="font-bold">Capture mode</label>
    <Select
      class="w-full! max-w-none!"
      fluid
      inputId="photo-preset"
      placeholder="Current stream snapshot"
      :modelValue="photo.selected_preset_id"
      :options="presetOptions"
      optionLabel="label"
      optionValue="value"
      :disabled="busy"
      @update:modelValue="selectPreset"
    />
    <p class="text-sm text-muted-color">
      Presets pause the preview while taking a fresh photo, then restore the
      stream. When detection and media overlays are enabled, detection runs on
      the captured photo. Presets are unavailable during video recording.
      Current stream snapshots keep the stream effects and overlay settings.
    </p>
    <div class="flex flex-wrap gap-2">
      <Button
        label="New preset"
        icon="pi pi-plus"
        :disabled="busy"
        @click="newPreset"
      />
      <Button
        v-if="selectedPreset"
        label="Edit"
        text
        :disabled="busy"
        @click="editPreset"
      />
      <Button
        v-if="selectedPreset"
        label="Delete"
        text
        severity="danger"
        :disabled="busy"
        @click="deletePreset"
      />
    </div>

    <div v-if="draft" class="flex flex-col gap-3 min-w-0">
      <label for="photo-name">Preset name</label>
      <InputText
        class="w-full! max-w-none!"
        fluid
        id="photo-name"
        v-model="draft.name"
        :maxlength="100"
        :disabled="busy"
      />
      <label for="photo-camera">Camera</label>
      <Select
        class="w-full! max-w-none!"
        fluid
        inputId="photo-camera"
        :modelValue="draft.camera.device"
        :options="cameraOptions"
        optionLabel="label"
        optionValue="value"
        :disabled="busy"
        @update:modelValue="selectCamera"
      />
      <label for="photo-mode">Available camera modes</label>
      <Select
        class="w-full! max-w-none!"
        fluid
        inputId="photo-mode"
        :options="modeOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Choose a mode"
        :disabled="busy"
        @update:modelValue="selectMode"
      />
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div class="flex flex-col gap-1 min-w-0">
          <label for="photo-width">Width</label>
          <InputNumber
            class="w-full! max-w-none!"
            inputClass="w-full! max-w-none!"
            inputId="photo-width"
            v-model="draft.camera.width"
            :min="1"
            :max="16384"
            :useGrouping="false"
            fluid
            :disabled="busy"
          />
        </div>
        <div class="flex flex-col gap-1 min-w-0">
          <label for="photo-height">Height</label>
          <InputNumber
            class="w-full! max-w-none!"
            inputClass="w-full! max-w-none!"
            inputId="photo-height"
            v-model="draft.camera.height"
            :min="1"
            :max="16384"
            :useGrouping="false"
            fluid
            :disabled="busy"
          />
        </div>
        <div class="flex flex-col gap-1 min-w-0">
          <label for="photo-fps">Capture FPS (optional)</label>
          <InputNumber
            class="w-full! max-w-none!"
            inputClass="w-full! max-w-none!"
            inputId="photo-fps"
            v-model="draft.camera.fps"
            :min="0.1"
            :max="240"
            :maxFractionDigits="3"
            fluid
            :disabled="busy"
          />
        </div>
      </div>
      <CameraControls
        id="photo-controls"
        v-model="draft.camera.controls"
        :device="draft.camera.device"
        :fps="draft.camera.fps"
        :disabled="busy"
      />
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div class="flex flex-col gap-1 min-w-0">
          <label for="photo-format">File format</label>
          <Select
            class="w-full! max-w-none!"
            fluid
            inputId="photo-format"
            v-model="draft.format"
            :options="formats"
            optionLabel="label"
            optionValue="value"
            :disabled="busy"
          />
        </div>
        <div v-if="draft.format === '.jpg'" class="flex flex-col gap-1 min-w-0">
          <label for="photo-quality">JPEG quality</label>
          <InputNumber
            class="w-full! max-w-none!"
            inputClass="w-full! max-w-none!"
            inputId="photo-quality"
            v-model="draft.quality"
            :min="0"
            :max="100"
            fluid
            :disabled="busy"
          />
        </div>
        <div class="flex flex-col gap-1 min-w-0">
          <label for="photo-rotation">Rotation</label>
          <Select
            class="w-full! max-w-none!"
            fluid
            inputId="photo-rotation"
            v-model="draft.rotation"
            :options="[0, 90, 180, 270]"
            :disabled="busy"
          />
        </div>
        <div class="flex flex-col gap-1 min-w-0">
          <label for="photo-effect">Effect</label>
          <Select
            class="w-full! max-w-none!"
            fluid
            inputId="photo-effect"
            v-model="draft.enhance_mode"
            :options="streamStore.enhancers"
            showClear
            placeholder="None"
            :disabled="busy"
          />
        </div>
        <div class="flex flex-col gap-1 min-w-0">
          <label for="photo-settle">Settling time (seconds)</label>
          <InputNumber
            class="w-full! max-w-none!"
            inputClass="w-full! max-w-none!"
            inputId="photo-settle"
            v-model="draft.settle_seconds"
            :min="0"
            :max="5"
            :step="0.1"
            :maxFractionDigits="1"
            fluid
            :disabled="busy"
          />
        </div>
      </div>
      <label class="flex items-center gap-2">
        <Checkbox
          v-model="draft.camera.use_gstreamer"
          binary
          :disabled="busy"
        />
        Use GStreamer (V4L2 cameras)
      </label>
      <p class="text-sm text-muted-color">
        Choose a supported camera mode, or enter dimensions within the camera's
        supported range. Settling time allows automatic exposure and focus to
        adjust before capture.
      </p>
      <div class="flex flex-wrap gap-2">
        <Button
          label="Save preset"
          :disabled="busy || !validDraft"
          :loading="settingsStore.savingPhotoSettings"
          @click="savePreset"
        />
        <Button label="Cancel" text :disabled="busy" @click="draft = null" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import {
  useCameraStore,
  useSettingsStore,
  useStreamStore,
} from "@/features/settings/stores";
import type { Device } from "@/features/settings/interface";
import type { PhotoPreset } from "@/features/settings/photo";
import { isStepwiseDevice } from "@/features/settings/components/camera/util";
import { cloneDeep } from "@/util/obj";
import { isNumber } from "@/util/guards";
import CameraControls from "@/features/settings/components/camera/CameraControls.vue";
import { validCameraControls } from "@/features/settings/camera-controls";

const cameraStore = useCameraStore();
const settingsStore = useSettingsStore();
const streamStore = useStreamStore();
const draft = ref<PhotoPreset | null>(null);
const photo = computed(
  () => settingsStore.data.photo ?? { presets: [], selected_preset_id: null },
);
const busy = computed(
  () => cameraStore.capturing || settingsStore.savingPhotoSettings,
);
const selectedPreset = computed(() =>
  photo.value.presets.find(
    (item) => item.id === photo.value.selected_preset_id,
  ),
);
const presetOptions = computed(() => [
  { label: "Current stream snapshot", value: null },
  ...photo.value.presets.map((item) => ({ label: item.name, value: item.id })),
]);
const cameraOptions = computed(() =>
  Array.from(
    new Map(
      cameraStore.devices.map((device) => [
        device.device,
        {
          label: device.name
            ? `${device.name} (${device.device})`
            : device.device,
          value: device.device,
        },
      ]),
    ).values(),
  ),
);
const modeOptions = computed(() =>
  cameraStore.devices
    .filter((device) => device.device === draft.value?.camera.device)
    .map((device) => ({
      label: isStepwiseDevice(device)
        ? `${device.pixel_format || "Auto"}: ${device.min_width}–${device.max_width} × ${device.min_height}–${device.max_height}`
        : `${device.width} × ${device.height}, ${device.fps || "auto"} FPS, ${device.pixel_format || "auto"}`,
      value: device,
    })),
);
const formats = [
  { label: "JPEG", value: ".jpg" },
  { label: "PNG", value: ".png" },
];
const validDraft = computed(() => {
  const item = draft.value;
  return (
    !!item &&
    !!item.name.trim() &&
    !!item.camera.device &&
    isNumber(item.camera.width) &&
    item.camera.width > 0 &&
    isNumber(item.camera.height) &&
    item.camera.height > 0 &&
    isNumber(item.quality) &&
    isNumber(item.settle_seconds) &&
    validCameraControls(item.camera.controls ?? {}, cameraStore.controlCapabilities[item.camera.device], item.camera.fps)
  );
});

const selectPreset = async (id: string | null) => {
  if (
    await settingsStore.savePhotoSettings({
      ...photo.value,
      selected_preset_id: id,
    })
  )
    draft.value = null;
};
const newPreset = () => {
  const camera = cameraStore.data;
  draft.value = {
    id: `photo-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: "High resolution photo",
    camera: {
      ...camera,
      device: camera.device || cameraOptions.value[0]?.value || "",
      width: camera.width || 1920,
      height: camera.height || 1080,
    },
    format: ".jpg",
    quality: 95,
    rotation: streamStore.data.rotation || 0,
    enhance_mode: null,
    settle_seconds: 0.5,
  };
};
const editPreset = () => {
  if (selectedPreset.value) draft.value = cloneDeep(selectedPreset.value);
};
const selectCamera = (device: string) => {
  if (!draft.value) return;
  draft.value.camera = {
    device,
    width: 1920,
    height: 1080,
    fps: null,
    use_gstreamer: false,
  };
};
const selectMode = (device: Device) => {
  if (!draft.value) return;
  draft.value.camera = {
    device: device.device,
    controls: draft.value.camera.controls,
    width: isStepwiseDevice(device) ? device.max_width : device.width,
    height: isStepwiseDevice(device) ? device.max_height : device.height,
    fps: isStepwiseDevice(device) ? null : device.fps,
    pixel_format: device.pixel_format,
    media_type: device.media_type,
    use_gstreamer: draft.value.camera.use_gstreamer,
  };
};
const savePreset = async () => {
  if (!draft.value || !validDraft.value) return;
  const preset = cloneDeep(draft.value);
  preset.name = preset.name.trim();
  const presets = photo.value.presets.some((item) => item.id === preset.id)
    ? photo.value.presets.map((item) => (item.id === preset.id ? preset : item))
    : [...photo.value.presets, preset];
  if (
    await settingsStore.savePhotoSettings({
      presets,
      selected_preset_id: preset.id,
    })
  )
    draft.value = null;
};
const deletePreset = async () => {
  const id = photo.value.selected_preset_id;
  if (
    await settingsStore.savePhotoSettings({
      presets: photo.value.presets.filter((item) => item.id !== id),
      selected_preset_id: null,
    })
  )
    draft.value = null;
};
</script>
