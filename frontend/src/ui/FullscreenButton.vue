<template>
  <button
    v-if="fullscreenEnabled"
    aria-label="Toggle fullscreen mode"
    v-tooltip="tooltipText"
    class="hover:text-primary-200 hover:bg-button-text-primary-hover-background px-1 rounded-sm bg-transparent transition-opacity duration-300 ease-in-out focus:opacity-70 focus:outline-none focus:ring-2 focus:ring-current"
    @click="handleToggleFullscreen"
  >
    <svg
      class="size-3"
      version="1.1"
      viewBox="0 0 14 14"
      xmlns="http://www.w3.org/2000/svg"
      xmlns:sketch="http://www.bohemiancoding.com/sketch/ns"
      xmlns:xlink="http://www.w3.org/1999/xlink"
    >
      <title />
      <desc />
      <defs />
      <g
        fill="none"
        fill-rule="evenodd"
        id="Page-1"
        stroke="none"
        stroke-width="1"
      >
        <g
          fill="currentColor"
          id="Core"
          transform="translate(-215.000000, -257.000000)"
        >
          <g id="fullscreen" transform="translate(215.000000, 257.000000)">
            <path
              d="M2,9 L0,9 L0,14 L5,14 L5,12 L2,12 L2,9 L2,9 Z M0,5 L2,5 L2,2 L5,2 L5,0 L0,0 L0,5 L0,5 Z M12,12 L9,12 L9,14 L14,14 L14,9 L12,9 L12,12 L12,12 Z M9,0 L9,2 L12,2 L12,5 L14,5 L14,0 L9,0 L9,0 Z"
              id="Shape"
            />
          </g>
        </g>
      </g>
    </svg>
  </button>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useFullscreen } from "@/composables/useFullscreen";

const { fullscreenEnabled, isFullscreen, handleToggleFullscreen } =
  useFullscreen();

const tooltipText = computed(() =>
  isFullscreen.value ? "Exit fullscreen" : "Enter fullscreen mode",
);
</script>
