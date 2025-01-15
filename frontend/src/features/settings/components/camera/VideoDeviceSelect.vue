<template>
  <div class="flex gap-2">
    <div class="flex-1">
      <Field :label="label">
        <TreeSelect
          @update:model-value="updateDevice"
          :nodes="devices"
          v-model:model-value="selectedDevice"
        />
      </Field>
    </div>

    <div class="flex-1">
      <SelectField
        optionLabel="label"
        optionValue="value"
        placeholder="Video Effect"
        field="video-size-preset"
        v-if="isStepwiseDevice(selectedDevice)"
        label="Resolutions Presets"
        :filter="false"
        v-model="stepwisePresetValue"
        :options="stepwisePresetOptions"
        @update:model-value="handleUpdateStepwisePreset"
      />
    </div>
  </div>
  <div class="flex gap-2 my-2">
    <div class="flex flex-1 gap-x-2">
      <NumberInputField
        :useGrouping="false"
        v-if="selectedDevice && (selectedDevice as any).max_width"
        fieldClassName="w-20"
        inputClass="w-20"
        label="Width"
        field="step-width"
        v-model="stepwiseData.width"
        :disabled="loading"
        :loading="loading"
        :min="selectedDevice && (selectedDevice as any).min_width"
        :max="selectedDevice && (selectedDevice as any).max_width"
        :invalid="!!invalidData.width"
        :message="invalidData.width"
        @input="handleChangeWidth"
        @update:model-value="validate"
        :step="invalidData.width ? 1 : (selectedDevice as any)?.width_step"
        @blur="validate"
      >
        <Slider
          class="my-2 cursor-pointer"
          v-if="selectedDevice && (selectedDevice as any).max_width"
          v-model="stepwiseData.width"
          :disabled="loading"
          :loading="loading"
          :min="selectedDevice && (selectedDevice as any).min_width"
          :max="selectedDevice && (selectedDevice as any).max_width"
          @update:model-value="validate"
          :step="invalidData.width ? 1 : (selectedDevice as any)?.width_step"
        />
      </NumberInputField>
      <NumberInputField
        inputClass="w-20"
        v-if="selectedDevice && (selectedDevice as any).max_width"
        label="Height"
        allowEmpty
        fieldClassName="w-20"
        field="step-height"
        v-model="stepwiseData.height"
        :disabled="loading"
        :loading="loading"
        :min="selectedDevice && (selectedDevice as any).min_height"
        :invalid="!!invalidData.height"
        :message="invalidData.height"
        @update:model-value="validate"
        @input="handleChangeHeight"
        :step="
          invalidData.height
            ? 1
            : selectedDevice && (selectedDevice as any).height_step
        "
        @blur="validate"
      >
        <Slider
          class="my-2 cursor-pointer"
          v-if="selectedDevice && (selectedDevice as any).max_width"
          v-model="stepwiseData.height"
          :disabled="loading"
          :loading="loading"
          :min="selectedDevice && (selectedDevice as any).min_height"
          :max="selectedDevice && (selectedDevice as any).max_height"
          @update:model-value="validate"
          :step="
            invalidData.height
              ? 1
              : selectedDevice && (selectedDevice as any).height_step
          "
        />
      </NumberInputField>
    </div>
    <div class="flex-1">
      <NumberInputField
        v-if="selectedDevice && (selectedDevice as any).max_width"
        label="FPS"
        allowEmpty
        inputClass="w-20"
        fieldClassName="w-20 self-end"
        field="step-fps"
        v-model="stepwiseData.fps"
        :disabled="loading"
        :loading="loading"
        :min="selectedDevice && (selectedDevice as any).min_fps"
        :max="selectedDevice && (selectedDevice as any).max_fps"
        :invalid="!!invalidData.fps"
        :message="invalidData.fps"
        @update:model-value="validate"
        @value-change="handleChangeFPS"
        @blur="validate"
      >
        <Slider
          class="my-2 cursor-pointer"
          v-if="selectedDevice && (selectedDevice as any).max_width"
          v-model="stepwiseData.fps"
          :disabled="loading"
          :loading="loading"
          :min="selectedDevice && (selectedDevice as any).min_fps"
          :max="selectedDevice && (selectedDevice as any).max_fps"
          @update:model-value="validate"
        />
      </NumberInputField>
    </div>
  </div>
  <div class="flex">
    <Button
      class="my-2"
      v-if="selectedDevice && (selectedDevice as any).max_width"
      :disabled="disabled || loading"
      @click="onSubmit"
      >Submit</Button
    >
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import type { InputNumberInputEvent } from "primevue/inputnumber";

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
import {
  presetOptions,
  PresetOptionValue,
} from "@/features/settings/components/camera/config";
import SelectField from "@/ui/SelectField.vue";
import { findStepwisePreset } from "@/features/settings/components/camera/util";

const camStore = useCameraStore();
const devices = computed(() => mapChildren(camStore.devices));

const isStepwiseDevice = (data: any): data is DeviceStepwise => data?.max_width;

const stepwiseData = ref({
  width: camStore.data.width,
  height: camStore.data.height,
  fps: camStore.data.fps,
});

const getInitialValue = () =>
  findDevice(camStore.data, camStore.devices) || null;

const selectedDevice = ref<DiscreteDevice | DeviceStepwise | null>(
  getInitialValue(),
);

const stepwisePresetValue = ref<PresetOptionValue | undefined>(
  findStepwisePreset(stepwiseData.value)?.value,
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

const handleUpdateStepwisePreset = (preset?: PresetOptionValue) => {
  if (preset?.width && preset?.height) {
    stepwiseData.value.width = preset.width;
    stepwiseData.value.height = preset.height;
  }
};

const stepwisePresetOptions = computed(() => {
  if (!isStepwiseDevice(selectedDevice.value)) {
    return [];
  }
  const { min_width, max_width, min_height, max_height } = selectedDevice.value;
  return presetOptions.filter(
    ({ value: { width, height } }) =>
      inRange(width, min_width, max_width) &&
      inRange(height, min_height, max_height),
  );
});

const validate = () => {
  invalidData.value = isStepwiseDevice(selectedDevice.value)
    ? validateStepwiseData(selectedDevice.value, stepwiseData.value)
    : {};
  return isEmpty(invalidData.value);
};

const handleChangeFPS = (newValue: number) => {
  stepwiseData.value.fps = newValue;
};

const handleChangeWidth = ({ value }: InputNumberInputEvent) => {
  stepwiseData.value.width = isNumber(value) ? value : undefined;
  validate();
};

const handleChangeHeight = ({ value }: InputNumberInputEvent) => {
  stepwiseData.value.height = isNumber(value) ? value : undefined;
  validate();
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
    stepwisePresetValue.value = findStepwisePreset(stepwiseData.value)?.value;

    onSubmit();
  }
};

onMounted(async () => {
  await camStore.fetchAllCameraSettings();
  selectedDevice.value = getInitialValue();
  stepwisePresetValue.value = findStepwisePreset(stepwiseData.value)?.value;
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

watch(
  () => stepwiseData.value,
  (newValue) => {
    stepwisePresetValue.value = findStepwisePreset(newValue)?.value;
  },
  { deep: true },
);
</script>
