<template>
  <FullscreenContent>
    <div class="resizable-wrapper" ref="resizableWrapper">
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

const Resizers = defineAsyncComponent({
  loader: () => import("@/ui/Resizers.vue"),
});

const props = defineProps<{
  fullscreen?: boolean;
  isResizable?: boolean;
  defaultWidth?: number;
  defaultHeight?: number;
  class?: string;
}>();
const defaultWidth = computed(() => props.defaultWidth || 800);
const defaultHeight = computed(() => props.defaultHeight || 600);

const aspectRatio = computed(() => defaultWidth.value / defaultHeight.value);
const isResizable = computed(() => props.isResizable);
const fullscreen = computed(() => props.fullscreen);

const windowInnerHeight = ref(window.innerHeight);
const windowInnerWidth = ref(window.innerWidth);
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
  size.value.width = defaultWidth.value;
  size.value.height = defaultHeight.value;
};

const handleResize = () => {
  windowInnerHeight.value = window.innerHeight;
  windowInnerWidth.value = window.innerWidth;

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
  if (fullscreen.value) {
    handleResize();
  } else {
    size.value.width = defaultWidth.value;
    size.value.height = defaultHeight.value;
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
});
</script>

<style scoped lang="scss">
.resizable-wrapper {
  position: relative;

  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  flex-direction: column;
}
</style>
