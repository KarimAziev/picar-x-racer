<template>
  <FullscreenContent>
    <div
      class="relative flex items-center justify-center select-none flex-col"
      ref="resizableWrapper"
    >
      <slot></slot>
      <component :is="Resizers" v-model="size" v-if="isResizable" />
    </div>
  </FullscreenContent>
</template>
<script setup lang="ts">
import {
  ref,
  watch,
  onMounted,
  onBeforeUnmount,
  computed,
  defineAsyncComponent,
} from "vue";

import FullscreenContent from "@/ui/FullscreenContent.vue";
import { useWindowSize } from "@/composables/useWindowSize";
import type { Nullable } from "@/util/ts-helpers";

const Resizers = defineAsyncComponent({
  loader: () => import("@/ui/Resizers.vue"),
});

const props = defineProps<{
  fullscreen?: boolean;
  isResizable?: boolean;
  defaultWidth?: Nullable<number>;
  defaultHeight?: Nullable<number>;
  class?: string;
}>();
const defaultWidth = computed(() => props.defaultWidth || 800);
const defaultHeight = computed(() => props.defaultHeight || 600);

const aspectRatio = computed(() => defaultWidth.value / defaultHeight.value);
const isResizable = computed(() => props.isResizable);
const fullscreen = computed(() => props.fullscreen);
const { height: windowInnerHeight, width: windowInnerWidth } = useWindowSize();

const size = ref({ width: 0, height: 0 });

const resizableWrapper = ref<HTMLDivElement | null>(null);

const setFullWidthHeight = () => {
  const ratio = windowInnerWidth.value / windowInnerHeight.value;

  if (ratio > aspectRatio.value) {
    // Window is wider than the aspect ratio
    size.value.height = windowInnerHeight.value;
    size.value.width = aspectRatio.value * windowInnerHeight.value;
  } else {
    // Window is taller than or equal to the aspect ratio
    size.value.width = windowInnerWidth.value;
    size.value.height = windowInnerWidth.value / aspectRatio.value;
  }
};

const resetSize = () => {
  if (
    windowInnerWidth.value >= defaultWidth.value &&
    windowInnerHeight.value >= defaultHeight.value
  ) {
    size.value.width = defaultWidth.value;
    size.value.height = defaultHeight.value;
  } else {
    setFullWidthHeight();
  }
};

const handleResize = () => {
  if (fullscreen.value) {
    setFullWidthHeight();
  }
};

watch(
  () => fullscreen.value,
  (newVal) => {
    if (newVal) {
      setFullWidthHeight();
    } else {
      resetSize();
    }
  },
);

watch(
  () => defaultWidth.value,
  (newVal) => {
    if (fullscreen.value) {
      setFullWidthHeight();
    } else {
      size.value.width = newVal;
    }
  },
);

watch(
  () => defaultHeight.value,
  (newVal) => {
    if (fullscreen.value) {
      setFullWidthHeight();
    } else {
      size.value.height = newVal;
    }
  },
);

watch(
  () => size.value.width,
  (newVal) => {
    if (resizableWrapper.value) {
      resizableWrapper.value.style.width = `${newVal}px`;
    }
  },
);
watch(
  () => size.value.height,
  (newVal) => {
    if (resizableWrapper.value) {
      resizableWrapper.value.style.height = `${newVal}px`;
    }
  },
);

onMounted(() => {
  window.addEventListener("resize", handleResize);
  window.addEventListener("orientationchange", handleResize);
  if (fullscreen.value) {
    handleResize();
  } else {
    size.value.width = defaultWidth.value;
    size.value.height = defaultHeight.value;
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  window.removeEventListener("orientationchange", handleResize);
});
</script>
