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
        fluid
        :useGrouping="false"
        v-if="selectedDevice && (selectedDevice as any).max_width"
        fieldClassName="w-20"
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
          v-model="stepwiseData.width as number"
          :disabled="loading"
          :loading="loading"
          :min="selectedDevice && (selectedDevice as any).min_width"
          :max="selectedDevice && (selectedDevice as any).max_width"
          @update:model-value="validate"
          :step="invalidData.width ? 1 : (selectedDevice as any)?.width_step"
        />
      </NumberInputField>
      <NumberInputField
        fluid
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
          v-model="stepwiseData.height as number"
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
        fluid
        v-if="selectedDevice && (selectedDevice as any).max_width"
        label="FPS"
        allowEmpty
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
          v-model="stepwiseData.fps as number"
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
import {
  findStepwisePreset,
  mapChildren,
  validateStepwiseData,
  isStepwiseDevice,
  groupDevices,
  extractDeviceAPI,
  findAlternative,
} from "@/features/settings/components/camera/util";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";

const camStore = useCameraStore();

const devices = computed(
  () => mapChildren(groupDevices(camStore.devices)) as DeviceNode[],
);

const useGstreamer = ref(camStore.data.use_gstreamer);

const stepwiseData = ref<Pick<CameraSettings, "width" | "fps" | "height">>({
  width: camStore.data.width || 0,
  height: camStore.data.height || 0,
  fps: camStore.data.fps || 30,
});

const getInitialValue = () =>
  (camStore.data.device &&
    findAlternative(
      camStore.data.device,
      camStore.data,
      devices.value,
      true,
    )) ||
  null;

const selectedDevice = ref<Device | null>(getInitialValue());

const stepwisePresetValue = ref<PresetOptionValue | undefined>(
  findStepwisePreset(stepwiseData.value)?.value,
);

const label = computed(() => {
  const val = selectedDevice.value?.device;
  const name = selectedDevice.value?.name;
  const camLabel = [name, val]
    .filter((v) => !!v)
    .sort((a, b) => (a?.length || 0) - (b?.length || 0))
    .join(": ");

  return camLabel.length > 0 ? camLabel : "Camera Device: ";
});

const invalidData = ref<Partial<Record<"width" | "height" | "fps", string>>>(
  {},
);

const handleUpdateStepwisePreset = (preset?: PresetOptionValue) => {
  if (preset?.width && preset?.height) {
    stepwiseData.value.width = preset.width;
    stepwiseData.value.height = preset.height;
    updateStepwiseDevice();
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
  validate();
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
      deviceData.width as number,
      stepwiseParams.min_width,
      stepwiseParams.max_width,
    ) ||
    !inRange(
      deviceData.height as number,
      stepwiseParams.min_height,
      stepwiseParams.max_height,
    ) ||
    (isNumber(deviceData.fps) &&
      !inRange(
        deviceData.fps,
        stepwiseParams.min_fps,
        stepwiseParams.max_fps,
      )) ||
    ((deviceData.width as number) - stepwiseParams.min_width) %
      stepwiseParams.width_step !==
      0 ||
    ((deviceData.height as number) - stepwiseParams.min_height) %
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
    width: roundNumber(deviceData.width as number),
    height: roundNumber(deviceData.height as number),
    fps: isNumber(deviceData.fps)
      ? roundNumber(deviceData.fps)
      : deviceData.fps,
  });
};

const updateDevice = async (deviceParams: Device) => {
  selectedDevice.value = deviceParams;

  const valid = validate();

  if (!deviceParams || !valid || isUnchanged()) {
    return deviceParams;
  }

  if ((deviceParams as any).width) {
    const discreted = deviceParams as DiscreteDevice;

    await camStore.updateData({
      ...discreted,
      use_gstreamer: useGstreamer.value,
    });
  } else if (isStepwiseDevice(deviceParams)) {
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

  const devicePath = selectedDevice.value?.device || camStore.data.device;
  const api = extractDeviceAPI(data.device);
  const isAutoToggle = value ? api !== "libcamera" : api === "libcamera";
  if (!isAutoToggle || !devicePath) {
    await Promise.all([camStore.updateData(data), camStore.fetchDevices()]);
    return;
  }

  const sizeData = isStepwiseDevice(selectedDevice.value)
    ? {
        width: stepwiseData.value.width,
        height: stepwiseData.value.height,
        pixel_format: selectedDevice.value.pixel_format,
        fps: stepwiseData.value.fps,
      }
    : (selectedDevice.value as DiscreteDevice);

  const alternative = findAlternative(devicePath, sizeData, devices.value);

  if (alternative && isStepwiseDevice(alternative)) {
    selectedDevice.value = alternative;
    stepwisePresetValue.value = findStepwisePreset(stepwiseData.value)?.value;
    if (validate()) {
      updateStepwiseDevice();
    }
  } else if (alternative) {
    await Promise.all([
      camStore.updateData({
        ...alternative,
        use_gstreamer: data.use_gstreamer,
      }),
      camStore.fetchDevices(),
    ]);
  } else {
    await Promise.all([camStore.updateData(data), camStore.fetchDevices()]);
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
      fps: camStore.data.fps || stepwiseData.value.fps,
    };
    useGstreamer.value = camStore.data.use_gstreamer;
    validate();
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
