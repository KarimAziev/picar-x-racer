<template>
  <SelectField
    label="Camera Device"
    field="video_feed_quality"
    v-model="selectedDevice"
    optionLabel="label"
    optionValue="value"
    :options="devices"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";

import { useSettingsStore, useCameraStore } from "@/features/settings/stores";

import { isString, isNumber } from "@/util/guards";
import SelectField from "@/ui/SelectField.vue";

const devices = computed(() =>
  [...camStore.devices].flatMap((item) => [...item.formats]),
);

const store = useSettingsStore();
const camStore = useCameraStore();
const isReady = ref(false);
const getInitialValue = () => {
  if (
    !isString(camStore.data.video_feed_device) ||
    !isString(camStore.data.video_feed_pixel_format) ||
    !isNumber(camStore.data.video_feed_fps) ||
    !isNumber(camStore.data.video_feed_height) ||
    !isNumber(camStore.data.video_feed_width)
  ) {
    return null;
  }
  const fps = camStore.data.video_feed_fps;
  const width = camStore.data.video_feed_width;
  const height = camStore.data.video_feed_height;
  const size = `${width}x${height}`;

  return `${camStore.data.video_feed_device}:${camStore.data.video_feed_pixel_format}:${size}:${fps}`;
};
const selectedDevice = ref<string | null>();

onMounted(async () => {
  await camStore.fetchCurrentSettings();
  await camStore.fetchDevices();
  selectedDevice.value = getInitialValue();
  isReady.value = true;
});

watch(
  () => selectedDevice.value,
  async (newVal) => {
    if (!isReady.value || !isString(newVal)) {
      return;
    }
    const [device, pixelFormat, size, fps] = newVal.split(":");
    const [width, height] = size.split("x");

    store.settings.video_feed_device = device;
    store.settings.video_feed_width = +width;
    store.settings.video_feed_height = +height;
    store.settings.video_feed_pixel_format = pixelFormat;
    store.settings.video_feed_fps = +fps;

    await camStore.updateCameraParams({
      video_feed_device: device,
      video_feed_pixel_format: pixelFormat,
      video_feed_width: +width,
      video_feed_height: +height,
      video_feed_fps: +fps,
    });
  },
);
</script>
<style scoped lang="scss"></style>
