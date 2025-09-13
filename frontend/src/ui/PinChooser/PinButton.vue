<template>
  <div class="flex items-center gap-4 shadow-sm">
    <button
      @click="handleClick"
      :class="[
        'rounded-full flex items-center justify-center border-2 p-2 w-28',
        !isDisabled
          ? 'bg-gradient-to-b from-[var(--p-primary-900)] to-[var(--p-primary-300)] cursor-pointer'
          : 'bg-slate-800 cursor-not-allowed',
        selected ? 'border-yellow-300 cursor-default' : 'border-gray-700',
        !selected && !isDisabled
          ? 'transition-opacity duration-300 ease-in-out hover:opacity-70 hover:bg-button-text-primary-hover-background focus:opacity-70 focus:outline-none focus:ring-current'
          : undefined,
      ]"
    >
      {{ pinValue }}
      <span
        :class="[
          'rounded-full',
          !isDisabled ? 'bg-primary-300' : 'bg-slate-600',
        ]"
      />
    </button>

    <div class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-3">
        <div class="truncate">
          <div
            class="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate"
          >
            {{ gpioLabel }}
            <span
              class="ml-2 text-xs font-medium text-gray-500 dark:text-gray-400"
            >
              #{{ pinInfo.number }}
            </span>
          </div>
          <div class="text-xs text-gray-500 dark:text-gray-400 truncate">
            {{ pinInfo.interfaces.join(", ") }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { PinInfo } from "@/features/settings/stores/device-info";
import type { Props as FieldProps } from "@/ui/Field.vue";

import { useDeviceInfoStore } from "@/features/settings/stores";
import { isNumber } from "@/util/guards";
import { powerLabels } from "@/ui/PinChooser/config";

const deviceInfoStore = useDeviceInfoStore();

export type ModelValue = string | number | null;

export interface Props extends FieldProps {
  label?: string;
  readonly?: boolean;
  disabled?: boolean;
  tooltip?: string;
  pinInfo: PinInfo;
  pinLayout?: string;
  selected?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:modelValue", value: ModelValue): void;
}>();

const pinExtended = computed(() =>
  deviceInfoStore.hash.get(props.pinInfo.name),
);

const pinValue = computed(() => {
  if (!props.pinLayout) {
    return props.pinInfo.name;
  }
  return pinExtended.value?.layouts[props.pinLayout] || props.pinInfo.name;
});

const isDisabled = computed(
  () => !pinExtended.value?.selectable || props.disabled || props.readonly,
);

const handleClick = () => {
  if (isDisabled.value) {
    return;
  }
  emit("update:modelValue", pinValue.value || null);
};

const gpioLabel = computed(() =>
  isNumber(props.pinInfo.gpio_number)
    ? `GPIO ${props.pinInfo.gpio_number}`
    : powerLabels[props.pinInfo.name] || "No GPIO",
);
</script>
