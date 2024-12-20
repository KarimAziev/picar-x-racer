import { ref, onMounted, onBeforeUnmount } from "vue";

export const useFullscreen = () => {
  const isFullscreen = ref(!!document.fullscreenElement);
  const fullscreenEnabled = ref(document.fullscreenEnabled);

  const handleToggleFullscreen = () => {
    if (!isFullscreen.value) {
      document.documentElement.requestFullscreen().catch((err) => {
        console.log(
          `Error attempting to enable fullscreen mode: ${err.message} (${err.name})`,
        );
      });
    } else {
      document.exitFullscreen();
    }
  };

  const handleUpdateIsFullscreen = () => {
    isFullscreen.value = !!document.fullscreenElement;
  };

  const removeResizeListeners = () => {
    window.removeEventListener("fullscreenchange", handleUpdateIsFullscreen);
  };
  const addResizeListeners = () => {
    removeResizeListeners();
    window.addEventListener("fullscreenchange", handleUpdateIsFullscreen);
  };

  onMounted(() => {
    handleUpdateIsFullscreen();
    addResizeListeners();
  });
  onBeforeUnmount(removeResizeListeners);
  return {
    isFullscreen,
    addResizeListeners,
    removeResizeListeners,
    handleToggleFullscreen,
    fullscreenEnabled,
  };
};
