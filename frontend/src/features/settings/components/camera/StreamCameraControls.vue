<template>
  <div class="flex flex-col gap-3">
    <CameraControls
      id="stream-controls"
      v-model="draft"
      :device="camera.data.device"
      :fps="camera.data.fps"
      :disabled="busy"
    />
    <Button
      label="Apply camera controls"
      :disabled="busy || !valid || !camera.data.device"
      :loading="camera.loading"
      @click="apply"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import CameraControls from "@/features/settings/components/camera/CameraControls.vue";
import { useCameraStore } from "@/features/settings/stores";
import {
  validCameraControls,
  type CameraControls as Controls,
} from "@/features/settings/camera-controls";

const camera = useCameraStore();
const draft = ref<Controls>({});
const busy = computed(
  () =>
    camera.loading ||
    camera.capturing ||
    camera.controlsLoading[camera.data.device ?? ""],
);
const valid = computed(() =>
  validCameraControls(
    draft.value,
    camera.controlCapabilities[camera.data.device ?? ""],
    camera.data.fps,
  ),
);
watch(
  () => camera.data,
  (data) => {
    draft.value = { ...data.controls };
  },
  { immediate: true, deep: true },
);
const apply = () =>
  camera.updateData({ ...camera.data, controls: { ...draft.value } });
</script>
