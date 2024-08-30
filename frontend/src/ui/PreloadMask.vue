<template>
  <transition name="fade">
    <div class="wrapper" v-if="showPreloader">
      <div class="content">
        <ResizableContainer
          :default-width="640"
          :default-height="480"
          :fullscreen="true"
        >
          <ScanLines class="box" />
        </ResizableContainer>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref } from "vue";

import ResizableContainer from "@/ui/ResizableContainer.vue";
import ScanLines from "@/ui/ScanLines.vue";

const props = defineProps<{ loading?: boolean; delay?: number }>();

const showPreloader = ref(false);
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

<style scoped lang="scss">
.wrapper {
  width: 100%;
  display: flex;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 15;
}

.content {
  flex: auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.box {
  width: 100%;
  height: 100%;
  opacity: 1;
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);
  user-select: none;
}

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
