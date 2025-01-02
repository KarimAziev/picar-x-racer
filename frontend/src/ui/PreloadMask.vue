<template>
  <transition name="fade">
    <div
      class="fixed inset-0 flex items-center justify-center z-50 w-full h-full"
      v-if="showPreloader"
    >
      <div class="flex items-center justify-center flex-auto">
        <ResizableContainer
          :default-width="width"
          :default-height="height"
          :fullscreen="true"
        >
          <ScanLines
            class="w-full h-full opacity-100 shadow-[0px_0px_4px_2px] shadow-primary"
          />
        </ResizableContainer>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref } from "vue";

import ResizableContainer from "@/ui/ResizableContainer.vue";
import ScanLines from "@/ui/ScanLines.vue";
import { useWindowSize } from "@/composables/useWindowSize";

const props = defineProps<{ loading?: boolean; delay?: number }>();

const showPreloader = ref(false);
const { width, height } = useWindowSize();

let animationFrameId;

const initPreloader = () => {
  setTimeout(() => {
    showPreloader.value = true;
    const startTime = performance.now();
    const duration = props.delay ?? 500;

    const hidePreloader = (currentTime: number) => {
      const elapsedTime = currentTime - startTime;
      if (elapsedTime >= duration) {
        showPreloader.value = false;
      } else {
        animationFrameId = requestAnimationFrame(hidePreloader);
      }
    };

    animationFrameId = requestAnimationFrame(hidePreloader);
  }, 100);
};

if (props.loading) {
  initPreloader();
} else {
  showPreloader.value = false;
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition:
    opacity 2s,
    visibility 2s;
  visibility: visible;
}

.fade-enter,
.fade-leave-to {
  opacity: 0;
  visibility: hidden;
}
</style>
