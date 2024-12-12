<template>
  <Field :label="label"
    ><TreeSelect
      inputId="device"
      v-model="selectedDevice"
      :options="devices"
      :disabled="loading"
      :loading="loading"
      @update:model-value="updateDevice"
  /></Field>
</template>

<script setup lang="ts">
import TreeSelect from "primevue/treeselect";
import { ref, onMounted, computed, watch } from "vue";

import { useCameraStore } from "@/features/settings/stores";

import { isString, isNumber } from "@/util/guards";
import Field from "@/ui/Field.vue";
import { DeviceSuboption } from "@/features/settings/stores/camera";

const camStore = useCameraStore();
const devices = computed(() => camStore.devices);

type DeviceTreeValue = { [key: string]: boolean };

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

const getInitialValue = () => {
  if (
    !isString(camStore.data.device) ||
    !isString(camStore.data.pixel_format) ||
    !isNumber(camStore.data.fps) ||
    !isNumber(camStore.data.height) ||
    !isNumber(camStore.data.width)
  ) {
    return {};
  }
  const fps = camStore.data.fps;
  const width = camStore.data.width;
  const height = camStore.data.height;
  const size = `${width}x${height}`;

  return {
    [`${camStore.data.device}:${camStore.data.pixel_format}:${size}:${fps}`]:
      true,
  };
};

const selectedDevice = ref<DeviceTreeValue>(getInitialValue());
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
  () => camStore.data,
  () => {
    selectedDevice.value = getInitialValue();
  },
);

const updateDevice = async (newValObj: DeviceTreeValue) => {
  const newVal = Object.keys(newValObj)[0];
  if (!isString(newVal)) {
    return;
  }
  const itemData = hashData.value[newVal];
  if (!itemData) {
    return itemData;
  }
  const { pixel_format, fps, size, device } = itemData;

  const [width, height] = size.split("x");
  await camStore.updateData({
    device: device,
    pixel_format: pixel_format,
    width: +width,
    height: +height,
    fps: +fps,
  });
};
</script>
<style scoped lang="scss"></style>
