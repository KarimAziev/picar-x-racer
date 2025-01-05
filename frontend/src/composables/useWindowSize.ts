import { ref, onMounted, onBeforeUnmount } from "vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";

export const useWindowSize = () => {
  const isMobile = useDeviceWatcher();
  const getHeight = () =>
    isMobile.value
      ? Math.min(window.screen.availHeight, window.innerHeight)
      : window.innerHeight;

  const getWidth = () =>
    isMobile.value
      ? Math.min(window.screen.availWidth, window.innerWidth)
      : window.innerWidth;

  const width = ref(getWidth());
  const height = ref(getHeight());
  const handleResize = () => {
    width.value = getWidth();
    height.value = getHeight();
  };

  const addResizeListeners = () => {
    window.addEventListener("resize", handleResize);
  };

  const removeResizeListeners = () => {
    window.removeEventListener("resize", handleResize);
  };

  onMounted(() => {
    handleResize();
    addResizeListeners();
  });
  onBeforeUnmount(removeResizeListeners);
  return {
    width,
    height,
    addResizeListeners,
    removeResizeListeners,
  };
};
