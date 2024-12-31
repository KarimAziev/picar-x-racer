<template>
  <Field :label="label">
    <TreeSelect
      @update:model-value="updateDevice"
      :nodes="devices"
      v-model:model-value="selectedDevice"
    />
  </Field>
  <NumberInputField
    v-if="selectedDevice && (selectedDevice as any).max_width"
    label="Width"
    field="step-width"
    v-model="stepwiseData.width"
    :disabled="loading"
    :loading="loading"
    suffix="px"
    :min="selectedDevice && (selectedDevice as any).min_width"
    :max="selectedDevice && (selectedDevice as any).max_width"
    :invalid="!!invalidData.width"
    :message="invalidData.width"
    @update:model-value="validate"
    :step="invalidData.width ? 1 : (selectedDevice as any)?.width_step"
    @blur="validate"
  />
  <NumberInputField
    v-if="selectedDevice && (selectedDevice as any).max_width"
    label="Height"
    allowEmpty
    suffix="px"
    field="step-height"
    v-model="stepwiseData.height"
    :disabled="loading"
    :loading="loading"
    :min="selectedDevice && (selectedDevice as any).min_height"
    :invalid="!!invalidData.height"
    :message="invalidData.height"
    @update:model-value="validate"
    :step="
      invalidData.height
        ? 1
        : selectedDevice && (selectedDevice as any).height_step
    "
    @blur="validate"
  />
  <NumberInputField
    v-if="selectedDevice && (selectedDevice as any).max_width"
    label="FPS"
    allowEmpty
    field="step-fps"
    v-model="stepwiseData.fps"
    :disabled="loading"
    :loading="loading"
    :min="selectedDevice && (selectedDevice as any).min_fps"
    :max="selectedDevice && (selectedDevice as any).max_fps"
    :invalid="!!invalidData.fps"
    :message="invalidData.fps"
    @update:model-value="validate"
    @blur="validate"
  />
  <Button
    v-if="selectedDevice && (selectedDevice as any).max_width"
    :disabled="disabled || loading"
    @click="onSubmit"
    >Submit</Button
  >
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";

import { useCameraStore } from "@/features/settings/stores";

import Field from "@/ui/Field.vue";
import {
  findDevice,
  mapChildren,
  validateStepwiseData,
} from "@/features/settings/util";
import { DiscreteDevice, DeviceStepwise } from "@/features/settings/interface";

import TreeSelect from "@/ui/TreeSelect.vue";
import { roundNumber } from "@/util/number";
import { isNumber, isEmpty } from "@/util/guards";
import { inRange } from "@/util/number";
import NumberInputField from "@/ui/NumberInputField.vue";
import { where } from "@/util/func";

const camStore = useCameraStore();
const devices = computed(() => mapChildren(camStore.devices));
const isStepwiseDevice = (data: any): data is DeviceStepwise => data?.max_width;

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

const invalidData = ref<Partial<Record<"width" | "height" | "fps", string>>>(
  {},
);

const validate = () => {
  invalidData.value = isStepwiseDevice(selectedDevice.value)
    ? validateStepwiseData(selectedDevice.value, stepwiseData.value)
    : {};
  return isEmpty(invalidData.value);
};

const isUnchanged = () => {
  const sizeData = isStepwiseDevice(selectedDevice.value)
    ? stepwiseData.value
    : (selectedDevice.value as DiscreteDevice);

  return where(
    {
      device: (v) => v === selectedDevice.value?.device,
      pixel_format: (v) => v === selectedDevice.value?.pixel_format,
      width: (v) => v === sizeData.width,
      height: (v) => v === sizeData.height,
      fps: (v) => v === sizeData.fps,
    },
    camStore.data,
  );
};

const disabled = computed(
  () => !isEmpty(invalidData.value) || !selectedDevice.value || isUnchanged(),
);

const loading = computed(() => camStore.loading);

const updateStepwiseDevice = async (deviceData: {
  width?: number;
  height?: number;
  fps?: number;
}) => {
  if (!isStepwiseDevice(selectedDevice.value)) {
    return;
  }

  const stepwiseParams = selectedDevice.value;

  if (
    !where({ width: isNumber, height: isNumber, fps: isNumber }, deviceData) ||
    !inRange(
      deviceData.width,
      stepwiseParams.min_width,
      stepwiseParams.max_width,
    ) ||
    !inRange(
      deviceData.height,
      stepwiseParams.min_height,
      stepwiseParams.max_height,
    ) ||
    !inRange(deviceData.fps, stepwiseParams.min_fps, stepwiseParams.max_fps) ||
    (deviceData.width - stepwiseParams.min_width) %
      stepwiseParams.width_step !==
      0 ||
    (deviceData.height - stepwiseParams.min_height) %
      stepwiseParams.height_step !==
      0
  ) {
    return;
  }

  await camStore.updateData({
    pixel_format: stepwiseParams.pixel_format,
    device: stepwiseParams.device,
    width: roundNumber(deviceData.width),
    height: roundNumber(deviceData.height),
    fps: roundNumber(deviceData.fps),
  });
};

const onSubmit = () => {
  if (disabled.value || !stepwiseData.value || !validate()) {
    return;
  }
  updateStepwiseDevice(stepwiseData.value);
};

const updateDevice = async (
  stepwiseParams: DiscreteDevice | DeviceStepwise,
) => {
  selectedDevice.value = stepwiseParams;
  const valid = validate();

  if (!stepwiseParams || !valid || isUnchanged()) {
    return stepwiseParams;
  }

  if ((stepwiseParams as any).width) {
    const discreted = stepwiseParams as DiscreteDevice;

    await camStore.updateData(discreted);
  } else if (isStepwiseDevice(stepwiseParams)) {
    onSubmit();
  }
};

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
</script>
<style scoped lang="scss"></style>
