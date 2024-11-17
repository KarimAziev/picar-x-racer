<template>
  <Field :label="label"
    ><TreeSelect
      inputId="video_feed_device"
      v-model="selectedDevice"
      :options="devices"
      :disabled="loading"
      :loading="loading"
  /></Field>
</template>

<script setup lang="ts">
import TreeSelect from "primevue/treeselect";
import { ref, onMounted, computed, watch } from "vue";

import { useSettingsStore, useCameraStore } from "@/features/settings/stores";

import { isString, isNumber } from "@/util/guards";
import Field from "@/ui/Field.vue";
import { DeviceSuboption } from "@/features/settings/stores/camera";

const store = useSettingsStore();
const camStore = useCameraStore();
const devices = computed(() => camStore.devices);

const hashData = computed(() =>
  [...camStore.devices]
    .flatMap((item) => [...item.children])
    .reduce(
      (acc, item) => {
        acc[item.key] = item;
        return acc;
      },
      {} as { [key: string]: DeviceSuboption },
    ),
);

const loading = computed(() => camStore.loading);

const isReady = ref(false);
const getInitialValue = () => {
  if (
    !isString(camStore.data.video_feed_device) ||
    !isString(camStore.data.video_feed_pixel_format) ||
    !isNumber(camStore.data.video_feed_fps) ||
    !isNumber(camStore.data.video_feed_height) ||
    !isNumber(camStore.data.video_feed_width)
  ) {
    return {};
  }
  const fps = camStore.data.video_feed_fps;
  const width = camStore.data.video_feed_width;
  const height = camStore.data.video_feed_height;
  const size = `${width}x${height}`;

  return {
    [`${camStore.data.video_feed_device}:${camStore.data.video_feed_pixel_format}:${size}:${fps}`]:
      true,
  };
};

const selectedDevice = ref<{ [key: string]: boolean }>(getInitialValue());
const label = computed(() => {
  const val = Object.keys(selectedDevice.value)[0];

  return [`Camera:`, val ? val.split(":")[0] : val]
    .filter((v) => !!v)
    .join(" ");
});

onMounted(async () => {
  await camStore.fetchAllCameraSettings();
  selectedDevice.value = getInitialValue();
});

watch(
  () => selectedDevice.value,
  async (newValObj) => {
    const newVal = Object.keys(newValObj)[0];
    if (!isString(newVal)) {
      return;
    }
    if (!isReady.value) {
      isReady.value = true;
      return;
    }
    const itemData = hashData.value[newVal];
    if (!itemData) {
      return itemData;
    }
    const { pixel_format, fps, size, device } = itemData;

    const [width, height] = size.split("x");

    store.settings.video_feed_device = device;
    store.settings.video_feed_width = +width;
    store.settings.video_feed_height = +height;
    store.settings.video_feed_pixel_format = pixel_format;
    store.settings.video_feed_fps = +fps;

    await camStore.updateCameraParams({
      video_feed_device: device,
      video_feed_pixel_format: pixel_format,
      video_feed_width: +width,
      video_feed_height: +height,
      video_feed_fps: +fps,
    });
  },
);
</script>
<style scoped lang="scss"></style>
