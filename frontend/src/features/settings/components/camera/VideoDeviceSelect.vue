<template>
  <Field :label="label" v-tooltip="'The camera device path and settings'"
    ><TreeSelect
      selectionMode="single"
      inputId="device"
      v-model="selectedDevice"
      :options="devices"
      :disabled="loading"
      :loading="loading"
      @update:model-value="updateDevice"
    />
  </Field>
  <VideoStepwiseDevice
    v-if="stepwiseDevice"
    v-bind="stepwiseDevice"
    @update:model-value="updateStepwiseDevice"
  />
</template>

<script setup lang="ts">
import TreeSelect from "primevue/treeselect";
import { ref, onMounted, computed, watch } from "vue";

import { useCameraStore } from "@/features/settings/stores";

import { isString } from "@/util/guards";
import Field from "@/ui/Field.vue";
import {
  findDevice,
  extractChildren,
  mapChildren,
} from "@/features/settings/util";
import { DiscreteDevice, DeviceStepwise } from "@/features/settings/interface";
import VideoStepwiseDevice from "@/features/settings/components/camera/VideoStepwiseDevice.vue";

const camStore = useCameraStore();
const devices = computed(() => mapChildren(camStore.devices));

type DeviceTreeValue = { [key: string]: boolean };

const loading = computed(() => camStore.loading);

const getInitialValue = () => {
  const found = findDevice(camStore.data, camStore.devices);
  if (!found) {
    return {};
  }

  return {
    [found.key]: true,
  };
};

const selectedDevice = ref<DeviceTreeValue>(getInitialValue());

const label = computed(() => {
  const val = Object.keys(selectedDevice.value)[0];

  return [`Camera:`, val ? val.split(":")[0] : val]
    .filter((v) => !!v)
    .join(" ");
});

const stepwiseDevice = computed(() => {
  const newVal = Object.keys(selectedDevice.value)[0];
  if (!isString(newVal)) {
    return;
  }
  const itemData = extractChildren(camStore.devices).find(
    (item) => item.key === newVal,
  );
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

const updateDevice = async (newValObj: DeviceTreeValue) => {
  const newVal = Object.keys(newValObj)[0];
  if (!isString(newVal)) {
    return;
  }
  const itemData = extractChildren(camStore.devices).find(
    (item) => item.key === newVal,
  );
  if (!itemData) {
    return itemData;
  }
  if ((itemData as any).width) {
    const discreted = itemData as DiscreteDevice;
    await camStore.updateData(discreted);
  }
};
</script>
<style scoped lang="scss"></style>
