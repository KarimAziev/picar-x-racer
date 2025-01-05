<template>
  <button
    v-if="fullscreenEnabled"
    aria-label="Toggle fullscreen mode"
    v-tooltip="tooltipText"
    class="hover:text-primary-200"
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
    <!-- <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="currentColor"
      class="size-3"
      viewBox="0 0 16 16"
    >
      <path
        d="M1.5 1a.5.5 0 0 0-.5.5v4a.5.5 0 0 1-1 0v-4A1.5 1.5 0 0 1 1.5 0h4a.5.5 0 0 1 0 1zM10 .5a.5.5 0 0 1 .5-.5h4A1.5 1.5 0 0 1 16 1.5v4a.5.5 0 0 1-1 0v-4a.5.5 0 0 0-.5-.5h-4a.5.5 0 0 1-.5-.5M.5 10a.5.5 0 0 1 .5.5v4a.5.5 0 0 0 .5.5h4a.5.5 0 0 1 0 1h-4A1.5 1.5 0 0 1 0 14.5v-4a.5.5 0 0 1 .5-.5m15 0a.5.5 0 0 1 .5.5v4a1.5 1.5 0 0 1-1.5 1.5h-4a.5.5 0 0 1 0-1h4a.5.5 0 0 0 .5-.5v-4a.5.5 0 0 1 .5-.5"
      />
    </svg> -->
    <!-- <svg
      class="size-3"
      fill="currentColor"
      version="1.1"
      id="Layer_1"
      xmlns="http://www.w3.org/2000/svg"
      xmlns:xlink="http://www.w3.org/1999/xlink"
      viewBox="0 0 512 512"
      xml:space="preserve"
    >
      <g>
        <g>
          <path
            d="M0,0v512h512V0H0z M477.867,477.867H34.133V34.133h443.733V477.867z"
          />
        </g>
      </g>
      <g>
        <g>
          <polygon
            points="126.533,102.4 199.111,102.4 199.111,68.267 68.267,68.267 68.267,199.111 102.4,199.111 102.4,126.538
			198.422,222.558 222.556,198.423 		"
          />
        </g>
      </g>
      <g>
        <g>
          <polygon
            points="222.557,313.581 198.422,289.445 102.4,385.467 102.4,312.889 68.267,312.889 68.267,443.733 199.111,443.733
			199.111,409.6 126.538,409.6 		"
          />
        </g>
      </g>
      <g>
        <g>
          <polygon
            points="409.6,312.889 409.6,385.467 313.578,289.444 289.444,313.578 385.462,409.6 312.889,409.6 312.889,443.733
			443.733,443.733 443.733,312.889 		"
          />
        </g>
      </g>
      <g>
        <g>
          <polygon
            points="312.889,68.267 312.889,102.4 385.467,102.4 289.444,198.423 313.578,222.558 409.6,126.538 409.6,199.111
			443.733,199.111 443.733,68.267 		"
          />
        </g>
      </g>
    </svg> -->
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
