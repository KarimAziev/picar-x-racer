<template>
  <div class="flex gap-2">
    <div class="flex-1 min-w-0">
      <Field>
        <span
          v-tooltip="label"
          class="truncated-label truncate block font-bold"
          v-if="label"
          >{{ label }}
        </span>
        <TreeSelect
          @update:model-value="updateDevice"
          :nodes="devices"
          v-model:model-value="selectedDevice as unknown as TreeNode"
        />
      </Field>
    </div>

    <div class="flex-1 min-w-0" v-if="isStepwiseDevice(selectedDevice)">
      <SelectField
        optionLabel="label"
        optionValue="value"
        placeholder="Resolution"
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
  <div
    class="flex gap-2 my-2"
    v-if="selectedDevice && (selectedDevice as any).max_width"
  >
    <div class="flex flex-1 min-w-0 gap-x-2">
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
    <div class="flex-1 min-w-0 flex">
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
  <div class="flex my-2">
    <ToggleSwitchField
      field="use_gstreamer"
      layout="row-reverse"
      field-class-name="flex-row-reverse gap-2.5 items-center justify-end my-1"
      tooltip="Whether to use GStreamer"
      label="Use GStreamer"
      v-model="useGstreamer"
      @update:model-value="handleToggleGstreamer"
    />
  </div>
  <div class="flex my-2">
    <Button
      v-if="selectedDevice && (selectedDevice as any).max_width"
      :disabled="disabled || loading"
      @click="updateStepwiseDevice"
      >Submit</Button
    >
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import type { InputNumberInputEvent } from "primevue/inputnumber";
import type { TreeNode } from "@/ui/Tree.vue";
import { useCameraStore } from "@/features/settings/stores";
import Field from "@/ui/Field.vue";
import {
  findDevice,
  mapChildren,
  validateStepwiseData,
  isStepwiseDevice,
  isGstreamerStepwiseDevice,
  groupDevices,
  extractDeviceAPI,
  extractDeviceId,
} from "@/features/settings/util";
import {
  DiscreteDevice,
  CameraSettings,
  Device,
  DeviceNode,
} from "@/features/settings/interface";

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
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";

const camStore = useCameraStore();

const devices = computed(
  () => mapChildren(groupDevices(camStore.devices)) as DeviceNode[],
);

const useGstreamer = ref(camStore.data.use_gstreamer);

const stepwiseData = ref<Pick<CameraSettings, "width" | "fps" | "height">>({
  width: camStore.data.width || 0,
  height: camStore.data.height || 0,
  fps: camStore.data.fps,
});

const getInitialValue = () => findDevice(camStore.data, devices.value) || null;

const selectedDevice = ref(getInitialValue());

const stepwisePresetValue = ref<PresetOptionValue | undefined>(
  findStepwisePreset(stepwiseData.value)?.value,
);

const label = computed(() => {
  const val = selectedDevice.value?.device;
  const name = selectedDevice.value?.name;
  const camLabel = [name, val].filter((v) => !!v).join(": ");

  return camLabel.length > 0 ? camLabel : "Camera Device: ";
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
  const sizeData =
    isStepwiseDevice(selectedDevice.value) ||
    isGstreamerStepwiseDevice(selectedDevice.value)
      ? stepwiseData.value
      : (selectedDevice.value as DiscreteDevice);

  return (
    useGstreamer.value === camStore.data.use_gstreamer &&
    where(
      {
        device: (v) => v === selectedDevice.value?.device,
        pixel_format: (v) => v === selectedDevice.value?.pixel_format,
        width: (v) => v === sizeData.width,
        height: (v) => v === sizeData.height,
        fps: (v) => v === sizeData.fps,
        media_type: (v) => v === (selectedDevice.value as any).media_type,
      },
      camStore.data,
    )
  );
};

const disabled = computed(
  () => !isEmpty(invalidData.value) || !selectedDevice.value || isUnchanged(),
);

const loading = computed(() => camStore.loading);

const updateStepwiseDevice = async () => {
  if (disabled.value || !stepwiseData.value || !validate()) {
    return;
  }
  if (!isStepwiseDevice(selectedDevice.value)) {
    return;
  }

  const deviceData = stepwiseData.value;

  const stepwiseParams = selectedDevice.value;
  const isValid = where({ width: isNumber, height: isNumber }, deviceData);

  if (
    !isValid ||
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
    (isNumber(deviceData.fps) &&
      !inRange(
        deviceData.fps,
        stepwiseParams.min_fps,
        stepwiseParams.max_fps,
      )) ||
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
    use_gstreamer: useGstreamer.value,
    pixel_format: stepwiseParams.pixel_format,
    device: stepwiseParams.device,

    media_type: stepwiseParams.media_type,
    width: roundNumber(deviceData.width),
    height: roundNumber(deviceData.height),
    fps: isNumber(deviceData.fps)
      ? roundNumber(deviceData.fps)
      : deviceData.fps,
  });
};

const updateDevice = async (stepwiseParams: Device) => {
  selectedDevice.value = stepwiseParams;

  const valid = validate();

  if (!stepwiseParams || !valid || isUnchanged()) {
    return stepwiseParams;
  }

  if ((stepwiseParams as any).width) {
    const discreted = stepwiseParams as DiscreteDevice;

    await camStore.updateData({
      ...discreted,
      use_gstreamer: useGstreamer.value,
    });
  } else if (isStepwiseDevice(stepwiseParams)) {
    stepwisePresetValue.value = findStepwisePreset(stepwiseData.value)?.value;

    updateStepwiseDevice();
  }
};

const handleToggleGstreamer = async (value: boolean) => {
  useGstreamer.value = value;

  const data = {
    ...(selectedDevice.value ? selectedDevice.value : camStore.data),
    use_gstreamer: value,
  };

  const api = extractDeviceAPI(data.device);
  const sizeData = isStepwiseDevice(selectedDevice.value)
    ? stepwiseData.value
    : (selectedDevice.value as DiscreteDevice);

  if (value && api === "picamera2") {
    const valid = validate();
    const found =
      valid &&
      findDevice(
        {
          ...data,
          ...sizeData,
          device: `libcamera:${extractDeviceId(data.device)}`,
        },
        devices.value,
      );

    if (found) {
      data.device = found.device;
      await Promise.all([
        camStore.updateData({
          ...data,
          ...sizeData,
          ...found,
          device: found.device,
        }),
        camStore.fetchDevices(),
      ]);
    }
  } else if (!value && api === "libcamera") {
    const found = findDevice(
      {
        ...data,
        ...sizeData,
        device: `picamera2:${extractDeviceId(data.device)}`,
      },
      devices.value,
    );

    if (found) {
      await Promise.all([
        camStore.updateData({
          ...data,
          ...sizeData,
          ...found,
          device: found.device,
        }),
        camStore.fetchDevices(),
      ]);
    }
  } else {
    await Promise.all([camStore.updateData(data), camStore.fetchDevices()]);
  }

  selectedDevice.value = getInitialValue();
  stepwisePresetValue.value = findStepwisePreset(stepwiseData.value)?.value;
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
    useGstreamer.value = camStore.data.use_gstreamer;
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
