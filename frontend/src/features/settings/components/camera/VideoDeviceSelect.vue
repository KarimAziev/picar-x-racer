<template>
  <Field :label="label">
    <TreeSelect
      @update:model-value="updateDevice"
      :nodes="devices"
      v-model:model-value="selectedDevice"
    />
  </Field>
  <VideoStepwiseDevice
    v-if="selectedDevice && (selectedDevice as any).max_width"
    :min_fps="(selectedDevice as DeviceStepwise).min_fps"
    :max_fps="(selectedDevice as DeviceStepwise).max_fps"
    :min_width="(selectedDevice as DeviceStepwise).min_width"
    :max_width="(selectedDevice as DeviceStepwise).max_width"
    :min_height="(selectedDevice as DeviceStepwise).min_height"
    :max_height="(selectedDevice as DeviceStepwise).max_height"
    :height_step="(selectedDevice as DeviceStepwise).height_step"
    :width_step="(selectedDevice as DeviceStepwise).width_step"
    :modelValue="stepwiseData"
    @update:model-value="updateStepwiseDevice"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";

import { useCameraStore } from "@/features/settings/stores";

import Field from "@/ui/Field.vue";
import { findDevice, mapChildren } from "@/features/settings/util";
import { DiscreteDevice, DeviceStepwise } from "@/features/settings/interface";
import VideoStepwiseDevice from "@/features/settings/components/camera/VideoStepwiseDevice.vue";

import TreeSelect from "@/ui/TreeSelect.vue";
import { roundNumber } from "@/util/number";
import { isNumber } from "@/util/guards";
import { inRange } from "@/util/number";

const camStore = useCameraStore();
const devices = computed(() => mapChildren(camStore.devices));

const stepwiseData = ref({
  width: camStore.data.width,
  height: camStore.data.height,
  fps: camStore.data.fps,
});

const getInitialValue = () => {
  return findDevice(camStore.data, camStore.devices) || null;
};

const selectedDevice = ref<DiscreteDevice | DeviceStepwise | null>(
  getInitialValue(),
);

const label = computed(() => {
  const val = selectedDevice.value?.device;

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
    stepwiseData.value = {
      width: camStore.data.width,
      height: camStore.data.height,
      fps: camStore.data.fps,
    };
  },
);

const updateStepwiseDevice = async (params: {
  width?: number;
  height?: number;
  fps?: number;
}) => {
  const itemData = (selectedDevice.value as any)?.max_width
    ? (selectedDevice.value as DeviceStepwise)
    : null;
  if (
    !itemData ||
    !isNumber(params.width) ||
    !isNumber(params.height) ||
    !isNumber(params.fps) ||
    !inRange(params.width, itemData.min_width, itemData.max_width) ||
    !inRange(params.height, itemData.min_height, itemData.max_height) ||
    !inRange(params.fps, itemData.min_fps, itemData.max_fps)
  ) {
    return;
  }

  await camStore.updateData({
    pixel_format: itemData.pixel_format,
    device: itemData.device,
    width: roundNumber(params.width),
    height: roundNumber(params.height),
    fps: roundNumber(params.fps),
  });
};

const updateDevice = async (itemData: DiscreteDevice | DeviceStepwise) => {
  selectedDevice.value = itemData;
  if (!itemData) {
    return itemData;
  }
  if ((itemData as any).width) {
    const discreted = itemData as DiscreteDevice;
    await camStore.updateData(discreted);
  } else if ((itemData as any).max_width) {
    updateStepwiseDevice(stepwiseData.value);
  }
};
</script>
<style scoped lang="scss"></style>
