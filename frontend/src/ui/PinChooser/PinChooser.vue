<template>
  <div class="p-4 space-y-6">
    <SelectField
      label="Pin layout"
      :options="layoutOptions"
      v-model="selectedLayout"
    />
    <div
      v-for="(header, headerKey) in pinHeaders"
      :key="headerKey"
      class="bg-white/5 rounded-lg p-3 border border-gray-200/10"
    >
      <div class="flex items-center justify-between mb-3">
        <div class="text-lg font-semibold">{{ header.name }}</div>
      </div>
      <div class="flex gap-2">
        <div
          class="flex-1 gap-2"
          v-for="(pinRows, i) in groupColumnsSorted(header.pins)"
          :key="`${headerKey}-${i}`"
        >
          <div
            v-for="pin in pinRows"
            :key="`${headerKey}-${i}-${pin.name}`"
            class="p-2"
          >
            <PinButton
              :pin-info="pin"
              @update:model-value="(val) => emit('update:modelValue', val)"
              :pinLayout="selectedLayout"
              :selected="isSelected(pin)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type {
  PinInfo,
  PinMapping,
} from "@/features/settings/stores/device-info";
import { isString, isNumber } from "@/util/guards";
import type { Props as FieldProps } from "@/ui/Field.vue";
import SelectField from "@/ui/SelectField.vue";

import { useDeviceInfoStore } from "@/features/settings/stores";
import { pinValueLayout, groupColumnsSorted } from "@/ui/PinChooser/util";
import PinButton from "@/ui/PinChooser/PinButton.vue";

const deviceInfoStore = useDeviceInfoStore();

const pinHeaders = computed<PinMapping>(() => deviceInfoStore.pins);

const layoutOptions = computed(() => deviceInfoStore.layoutOptions);

export type ModelValue = string | number | null;

export interface Props extends FieldProps {
  modelValue: ModelValue;
  label?: string;
  readonly?: boolean;
  disabled?: boolean;
  tooltip?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:modelValue", value: ModelValue): void;
}>();

const modelNormalizedValue = computed(() =>
  isNumber(props.modelValue)
    ? deviceInfoStore.hash.get(props.modelValue)?.name
    : props.modelValue,
);

const selectedLayout = ref(
  pinValueLayout(layoutOptions.value, modelNormalizedValue.value),
);

const isSelected = (pin: PinInfo | null | undefined) => {
  if (!pin) {
    return false;
  }
  if (isNumber(props.modelValue)) {
    return pin.gpio_number === props.modelValue;
  } else if (isString(props.modelValue)) {
    return (
      pin.name === props.modelValue ||
      (pin.names && pin.names.includes(props.modelValue))
    );
  } else {
    return false;
  }
};

watch(layoutOptions, (newVal) => {
  selectedLayout.value = pinValueLayout(newVal, modelNormalizedValue.value);
});
</script>
