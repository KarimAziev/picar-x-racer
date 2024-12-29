<template>
  <Field :label="label">
    <TreeSelect
      @update:model-value="updateDevice"
      :nodes="devices"
      v-model:model-value="selectedDevice"
    />
  </Field>
  <VideoStepwiseDevice
    v-if="stepwiseDevice"
    :min_fps="stepwiseDevice.min_fps"
    :max_fps="stepwiseDevice.max_fps"
    :min_width="stepwiseDevice.min_width"
    :max_width="stepwiseDevice.max_width"
    :min_height="stepwiseDevice.min_height"
    :max_height="stepwiseDevice.max_height"
    :height_step="stepwiseDevice.height_step"
    :width_step="stepwiseDevice.width_step"
    @update:model-value="updateStepwiseDevice"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";

import { useCameraStore } from "@/features/settings/stores";

import { isNumber } from "@/util/guards";
import Field from "@/ui/Field.vue";
import { findDevice, mapChildren } from "@/features/settings/util";
import { DiscreteDevice, DeviceStepwise } from "@/features/settings/interface";
import VideoStepwiseDevice from "@/features/settings/components/camera/VideoStepwiseDevice.vue";

import TreeSelect from "@/ui/TreeSelect.vue";

const camStore = useCameraStore();
const devices = computed(() => mapChildren(camStore.devices));

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

const stepwiseDevice = computed(() => {
  const itemData = selectedDevice.value;
  if (itemData && (itemData as any).max_width) {
    return itemData as DeviceStepwise;
  }
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

const updateStepwiseDevice = async (params: {
  width: number;
  height: number;
  fps: number;
}) => {
  if (!stepwiseDevice.value) {
    return;
  }
  await camStore.updateData({ ...stepwiseDevice.value, ...params });
};

const updateDevice = async (itemData: DiscreteDevice | DeviceStepwise) => {
  if (!itemData) {
    return itemData;
  }
  if ((itemData as any).width) {
    const discreted = itemData as DiscreteDevice;
    await camStore.updateData(discreted);
  } else if (
    isNumber(camStore.data.width) &&
    isNumber(camStore.data.height) &&
    isNumber(camStore.data.fps)
  ) {
    updateStepwiseDevice({
      width: camStore.data.width,
      height: camStore.data.height,
      fps: camStore.data.fps,
    });
  }
};
</script>
<style scoped lang="scss"></style>
