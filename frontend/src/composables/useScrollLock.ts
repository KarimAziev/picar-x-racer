import { onMounted, ref, onBeforeUnmount } from "vue";

export const useScrollLock = () => {
  const initialInnerHeight = ref(window.innerHeight);
  const isFullscreen = ref();

  const updateAppHeight = () => {
    const vh = window.innerHeight * 0.01;

    document.documentElement.style.setProperty("--app-height", `${vh * 100}px`);
    if (window.innerHeight !== initialInnerHeight.value) {
      isFullscreen.value = true;
      unlockScroll();
      lockScroll();
    } else {
      isFullscreen.value = false;
      unlockScroll();
    }
  };

  const resetInitialHeight = () => {
    initialInnerHeight.value = window.innerHeight;
    isFullscreen.value = false;
  };

  const lockScroll = () => {
    document.addEventListener("scroll", preventScroll, { passive: false });
    document.addEventListener("touchmove", preventScroll, { passive: false });
    document.addEventListener("wheel", preventScroll, { passive: false });
    document.body.style.position = "fixed";
  };

  const unlockScroll = () => {
    document.removeEventListener("scroll", preventScroll);
    document.removeEventListener("touchmove", preventScroll);
    document.removeEventListener("wheel", preventScroll);
    document.body.style.position = "";
  };

  const preventScroll = (e: Event) => {
    if (isFullscreen.value) {
      e.preventDefault();
    }
  };

  onMounted(() => {
    updateAppHeight();
    window.addEventListener("resize", updateAppHeight);
    window.addEventListener("orientationchange", resetInitialHeight);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", updateAppHeight);
    window.removeEventListener("orientationchange", resetInitialHeight);
  });
};
