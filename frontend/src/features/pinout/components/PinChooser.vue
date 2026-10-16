<template>
  <div class="md:p-2 lg:p-4">
    <p
      v-if="assignments"
      class="mb-3 text-[14px] text-slate-600 dark:text-slate-300"
    >
      Direct GPIO assignments include unsaved edits, not live activity.
      “Configured” means no enable switch. I²C channels are separate from GPIO
      pins.
    </p>
    <SelectField
      :filter="false"
      label="Pin Layout"
      class="text-[14px]"
      :options="layoutOptions"
      v-model="selectedLayout"
    />
    <p v-if="pinoutStore.loading" role="status" class="mt-3">
      Loading board pins…
    </p>
    <p v-else-if="!Object.keys(pinHeaders).length" role="status" class="mt-3">
      Board pin layout is unavailable.
    </p>
    <div
      v-else-if="unmappedAssignments.length"
      class="my-3 text-[14px] text-amber-800 dark:text-amber-300"
      role="status"
    >
      <p>These configured pins could not be matched to this board:</p>
      <ul class="list-disc pl-5">
        <li v-for="assignment in unmappedAssignments" :key="assignment.key">
          {{ assignment.owner }} · {{ assignment.field }}:
          {{ assignment.value }}
        </li>
      </ul>
    </div>
    <div v-for="(header, headerKey) in pinHeaders" :key="headerKey">
      <div class="flex items-center justify-between mb-3">
        <div class="text-[16px] font-semibold">{{ header.name }}</div>
      </div>
      <div
        class="grid grid-cols-1 sm:grid-cols-[repeat(var(--pin-columns),minmax(0,1fr))] gap-2 sm:gap-x-4"
        :style="{ '--pin-columns': header.columns }"
      >
        <PinButton
          v-for="pin in pinsInHeaderOrder(header.pins)"
          :key="`${headerKey}-${pin.number}`"
          :pin-info="pin"
          @update:model-value="(val) => emit('update:modelValue', val)"
          :pinLayout="selectedLayout"
          :selected="isSelected(pin)"
          :assignments="
            pin.gpio_number === null
              ? []
              : assignmentsByGpio.get(pin.gpio_number)
          "
          :show-usage="!!assignments"
          :current-assignment-key="currentAssignmentKey"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { isNumber } from "@/util/guards";
import SelectField from "@/ui/SelectField.vue";
import { useStore as usePinoutStore } from "@/features/pinout/store";
import {
  pinValueLayout,
  gpioForPin,
  groupPinAssignments,
} from "@/features/pinout/util";
import type { PinAssignment } from "@/features/pinout/usage";
import PinButton from "@/features/pinout/components/PinButton.vue";
import type { ModelValue } from "@/features/pinout/components/PinButton.vue";
import type { PinSchema, PinMapping } from "@/features/pinout/store";

const pinoutStore = usePinoutStore();

const pinHeaders = computed<PinMapping>(() => pinoutStore.pins);

const layoutOptions = computed(() => pinoutStore.layoutOptions);

export interface Props {
  modelValue: ModelValue;
  assignments?: PinAssignment[];
  currentAssignmentKey?: string;
}

const props = defineProps<Props>();

const assignmentsByGpio = computed(() =>
  groupPinAssignments(props.assignments || [], pinoutStore.hash),
);

const unmappedAssignments = computed(() =>
  (props.assignments || []).filter(
    (assignment) =>
      gpioForPin(assignment.value, pinoutStore.hash) === undefined,
  ),
);

const pinsInHeaderOrder = (pins: Record<string, PinSchema>) =>
  Object.values(pins).sort((a, b) => a.row - b.row || a.col - b.col);

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

const isSelected = (pin: PinSchema) =>
  pin.gpio_number !== null &&
  pin.gpio_number === gpioForPin(props.modelValue, pinoutStore.hash);

watch(layoutOptions, (newVal) => {
  selectedLayout.value = pinValueLayout(newVal, modelNormalizedValue.value);
});
</script>
