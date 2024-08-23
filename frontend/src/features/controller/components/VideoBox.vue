<template>
  <div class="video-box-container">
    <FullscreenToggle />
    <div class="video-box" ref="videoBox">
      <ImageFeed />
      <component :is="Resizers" v-model="size" v-if="isResizable" />
    </div>
  </div>
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
import ProgressSpinner from "primevue/progressspinner";
import { usePopupStore, useSettingsStore } from "@/features/settings/stores";
import FullscreenToggle from "@/features/controller/components/FullscreenToggle.vue";

const Resizers = defineAsyncComponent({
  loader: () => import("@/ui/Resizers.vue"),
  loadingComponent: ProgressSpinner,
  delay: 0,
});

const ImageFeed = defineAsyncComponent({
  loader: () => import("@/ui/ImageFeed.vue"),
  loadingComponent: ProgressSpinner,
  delay: 0,
});

const [defaultWidth, defaultHeight] = [1280, 720];
const aspectRatio = defaultWidth / defaultHeight;
const popupStore = usePopupStore();
const settingsStore = useSettingsStore();

const fullscreen = computed(() => settingsStore.settings.fullscreen);
const isResizable = computed(() => !popupStore.isOpen);

const windowInnerHeight = ref(window.innerHeight);
const windowInnerWidth = ref(window.innerWidth);
const size = ref({ width: defaultWidth, height: defaultHeight });

const videoBox = ref<HTMLDivElement | null>(null);

const setFullWidthHeight = () => {
  const ratio = windowInnerWidth.value / windowInnerHeight.value;

  if (ratio > aspectRatio) {
    // Window is wider than the aspect ratio
    size.value.height = windowInnerHeight.value;
    size.value.width = aspectRatio * windowInnerHeight.value;
  } else {
    // Window is taller than or equal to the aspect ratio
    size.value.width = windowInnerWidth.value;
    size.value.height = windowInnerWidth.value / aspectRatio;
  }
};

const resetSize = () => {
  size.value.width = defaultWidth;
  size.value.height = defaultHeight;
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
  () => size.value.width,
  (newVal) => {
    if (videoBox.value) {
      videoBox.value.style.width = `${newVal}px`;
    }
  },
);
watch(
  () => size.value.height,
  (newVal) => {
    if (videoBox.value) {
      videoBox.value.style.height = `${newVal}px`;
    }
  },
);

onMounted(() => {
  window.addEventListener("resize", handleResize);
  if (fullscreen.value) {
    handleResize();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
});
</script>

<style scoped lang="scss">
.video-box-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  height: 100vh;
  color: var(--p-primary-200);
}

.video-box {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
}
</style>
