<template>
  <div class="relative flex items-center">
    <div class="relative text-inherit" v-tooltip.left="tooltipText">
      <i
        class="pi pi-sync animate-spin absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
        v-if="loading"
      />
      <div class="flex items-center w-[12px] relative h-[15px]">
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
    <div class="flex flex-col md:flex-row">
      <component :is="tagName" class="max-w-10 md:max-w-14 truncate font-medium"
        >{{ name }}:&nbsp;</component
      >

      <component
        :is="tagName"
        class="max-w-10 md:max-w-14 truncate overflow-y-visible"
      >
        {{ voltage ?? "--" }}V
      </component>
      <component :is="tagName" v-if="!isMobile && voltage && current"
        >/</component
      >
      <component
        :is="tagName"
        class="max-w-10 truncate md:max-w-14 relative -top-1 sm:top-0"
        v-if="current !== null && current !== undefined"
      >
        {{ current }}A
      </component>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
const props = defineProps<{
  name: string;
  voltage?: number | null;
  current?: number | null;
  percentage?: number | null;
  error?: string | null;
  loading?: boolean;
}>();

const baseHeight = 14;

const isMobile = useDeviceWatcher();

const tagName = computed(() => (isMobile.value ? "small" : "span"));

const chargeHeight = computed(() =>
  Math.round(((props.percentage || 0) / 100) * (baseHeight - 1)),
);
const yHeight = computed(() => baseHeight - chargeHeight.value);

const tooltipText = computed(() => {
  if (props.error) return `${props.name}: ${props.error}`;
  const values = [
    props.percentage !== null && props.percentage !== undefined
      ? `${props.percentage}%`
      : null,
    props.voltage !== null && props.voltage !== undefined
      ? `${props.voltage}V`
      : null,
    props.current !== null && props.current !== undefined
      ? `${props.current}A`
      : null,
  ].filter(Boolean);
  return `${props.name}: ${values.join(", ") || "No reading"}`;
});
</script>
