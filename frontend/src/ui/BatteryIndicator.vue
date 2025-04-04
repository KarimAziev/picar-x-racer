<template>
  <div
    class="flex items-center text-inherit relative"
    v-tooltip.left="tooltipText"
  >
    <i
      class="pi pi-sync animate-spin absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
      v-if="loading"
    />
    <span
      class="bold min-w-11 transition-opacity"
      :class="{ ['opacity-0']: loading }"
    >
      {{ value }}V
    </span>

    <div class="flex items-center w-[12px] h-[15px] relative">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 12 18"
        class="block h-full"
      >
        <rect
          x="1"
          y="0.5"
          width="10"
          :height="baseHeight"
          rx="2"
          ry="2"
          stroke="currentColor"
          fill="none"
          stroke-width="1"
        />
        <rect
          x="4"
          y="-2"
          width="4"
          height="2"
          transform="translate(0,2)"
          fill="currentColor"
        />
        <rect
          x="2"
          :y="yHeight"
          :class="[loading && 'opacity-0']"
          width="8"
          :height="chargeHeight"
          fill="currentColor"
        />
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  value: number;
  percentage: number;
  loading?: boolean;
}>();

const baseHeight = 14;

const chargeHeight = computed(() =>
  Math.round((props.percentage / 100) * (baseHeight - 1)),
);
const yHeight = computed(() => baseHeight - chargeHeight.value);

const tooltipText = computed(() => `Battery ${props.percentage}%`);
</script>
