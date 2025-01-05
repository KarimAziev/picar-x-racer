<template>
  <div
    :class="class"
    class="flex items-center text-inherit"
    v-tooltip.left="`Battery ${percentage}%`"
  >
    <span class="bold min-w-11">{{ value }}V</span>
    <div class="flex items-center w-[12px] h-[15px]">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 12 18"
        class="block h-full"
      >
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
          :y="14 - chargeHeight"
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
  class?: string;
  value: number;
  percentage: number;
}>();

const chargeHeight = computed(() => Math.round((props.percentage / 100) * 13)); // Max height = 13
</script>
