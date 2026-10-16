<template>
  <div
    class="flex items-start gap-[12px] rounded-lg border p-[8px] min-w-0"
    :class="
      selected
        ? 'border-primary-500 bg-slate-50 dark:bg-slate-800'
        : 'border-slate-200 dark:border-slate-700'
    "
  >
    <button
      type="button"
      @click="handleClick"
      :disabled="isDisabled"
      :aria-pressed="!!selected"
      :aria-label="`${pinValue}, ${gpioLabel}, physical pin ${pinInfo.number}`"
      :aria-describedby="descriptionId"
      :class="[
        'rounded-full flex items-center justify-center border-2 px-2 min-h-[44px] w-[96px] text-[14px] shrink-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500',
        !isDisabled
          ? 'bg-slate-700 cursor-pointer text-white'
          : 'bg-slate-100 cursor-not-allowed text-slate-500 dark:bg-slate-800 dark:text-slate-400',
        selected
          ? 'border-primary-500 cursor-default shadow-sm'
          : 'border-transparent',
        !selected && !isDisabled ? 'hover:bg-slate-600' : undefined,
      ]"
    >
      {{ pinValue }}
    </button>

    <div :id="descriptionId" class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div
            class="text-[14px] font-semibold text-gray-900 dark:text-gray-100"
          >
            {{ gpioLabel }}
            <span
              class="ml-2 text-[12px] font-medium text-gray-500 dark:text-gray-400"
            >
              #{{ pinInfo.number }}
            </span>
            <span v-if="selected" class="ml-2 text-[12px]">Selected</span>
          </div>
          <div class="text-[12px] text-gray-500 dark:text-gray-400 break-words">
            {{ pinInfo.interfaces.join(", ") }}
          </div>
        </div>
      </div>
      <template v-if="showUsage && pinInfo.gpio_number !== null">
        <p
          v-if="assignments.length > 1"
          class="mt-1 text-[12px] font-semibold text-amber-800 dark:text-amber-300"
        >
          {{ assignments.length }} assignments
        </p>
        <ul v-if="assignments.length" class="mt-2 space-y-2 text-[12px]">
          <li
            v-for="assignment in assignments"
            :key="assignment.key"
            class="break-words"
          >
            <div class="font-medium text-slate-800 dark:text-slate-100">
              {{ assignment.owner }}
            </div>
            <div class="text-slate-600 dark:text-slate-300">
              {{ assignment.field }}
            </div>
            <div class="mt-1 flex flex-wrap gap-1">
              <span
                class="inline-flex items-center gap-1 rounded px-1.5 py-0.5"
                :class="
                  assignment.state === 'enabled'
                    ? 'bg-teal-100 text-teal-900 dark:bg-teal-950 dark:text-teal-200'
                    : assignment.state === 'disabled'
                      ? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                      : 'bg-blue-100 text-blue-900 dark:bg-blue-950 dark:text-blue-200'
                "
              >
                <i
                  :class="
                    assignment.state === 'disabled'
                      ? 'pi pi-pause-circle'
                      : 'pi pi-circle-fill'
                  "
                  aria-hidden="true"
                />
                {{
                  assignment.state === "enabled"
                    ? "Enabled"
                    : assignment.state === "disabled"
                      ? "Disabled"
                      : "Configured"
                }}
              </span>
              <span
                v-if="assignment.key === currentAssignmentKey"
                class="rounded px-1.5 py-0.5 border border-slate-400 text-slate-700 dark:text-slate-100"
              >
                This field
              </span>
            </div>
          </li>
        </ul>
        <p v-else class="mt-1 text-[12px] text-slate-500 dark:text-slate-400">
          Unassigned
        </p>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, useId } from "vue";
import type { PinSchema } from "@/features/pinout/store";
import { useStore as usePinoutStore } from "@/features/pinout/store";
import { isNumber } from "@/util/guards";
import { powerLabels } from "@/features/pinout/config";
import type { PinAssignment } from "@/features/pinout/usage";

const pinoutStore = usePinoutStore();

export type ModelValue = string | number | null;

export interface Props {
  readonly?: boolean;
  disabled?: boolean;
  pinInfo: PinSchema;
  pinLayout?: string;
  selected?: boolean;
  assignments?: PinAssignment[];
  showUsage?: boolean;
  currentAssignmentKey?: string;
}

const props = withDefaults(defineProps<Props>(), { assignments: () => [] });
const descriptionId = useId();

const emit = defineEmits<{
  (e: "update:modelValue", value: ModelValue): void;
}>();

const pinExtended = computed(() => pinoutStore.hash.get(props.pinInfo.name));

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
