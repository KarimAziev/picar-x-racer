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
import { isString, isNumber } from "@/util/guards";
import SelectField from "@/ui/SelectField.vue";
import { useStore as usePinoutStore } from "@/features/pinout/store";
import { pinValueLayout, groupColumnsSorted } from "@/features/pinout/util";
import PinButton from "@/features/pinout/components/PinButton.vue";
import type { ModelValue } from "@/features/pinout/components/PinButton.vue";
import type { PinSchema, PinMapping } from "@/features/pinout/store";

const pinoutStore = usePinoutStore();

const pinHeaders = computed<PinMapping>(() => pinoutStore.pins);

const layoutOptions = computed(() => pinoutStore.layoutOptions);

export interface Props {
  modelValue: ModelValue;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:modelValue", value: ModelValue): void;
}>();

const modelNormalizedValue = computed(() =>
  isNumber(props.modelValue)
    ? pinoutStore.hash.get(props.modelValue)?.name
    : props.modelValue,
);

const selectedLayout = ref(
  pinValueLayout(layoutOptions.value, modelNormalizedValue.value),
);

const isSelected = (pin: PinSchema | null | undefined) => {
  if (!pin) {
    return false;
  }
  return isNumber(props.modelValue)
    ? pin.gpio_number === props.modelValue
    : isString(props.modelValue)
      ? pin.name === props.modelValue ||
        (pin.names && pin.names.includes(props.modelValue))
      : false;
};

watch(layoutOptions, (newVal) => {
  selectedLayout.value = pinValueLayout(newVal, modelNormalizedValue.value);
});
</script>
