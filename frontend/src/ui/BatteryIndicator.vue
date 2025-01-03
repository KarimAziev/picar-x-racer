<template>
  <div :class="class" class="flex items-center text-inherit">
    <!-- Voltage Value -->
    <span class="min-w-[4rem] px-1">{{ value }}V</span>

    <!-- Battery Icon Wrapper -->
    <div class="flex items-center justify-center h-[15px] w-[12px]">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 12 16"
        class="h-full block"
      >
        <!-- Outer Battery -->
        <rect
          x="1"
          y="0.5"
          width="10"
          height="14"
          rx="2"
          ry="2"
          stroke="currentColor"
          fill="none"
          stroke-width="1"
        />
        <!-- Battery Cap -->
        <rect
          x="4"
          y="-2"
          width="4"
          height="2"
          transform="translate(0,2)"
          fill="currentColor"
        />
        <!-- Charge Level -->
        <rect
          x="2"
          :y="14 - chargeHeight"
          width="8"
          :height="chargeHeight"
          fill="currentColor"
        />
      </svg>
    </div>

    <!-- Percentage -->
    <span class="min-w-[4rem] px-1">{{ percentage }}%</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  class?: string;
  value: number;
  percentage: number;
}>();

const chargeHeight = computed(() => Math.round((props.percentage / 100) * 13)); // Max height = 13
</script>
