import { ref } from "vue";
import { usePopupStore } from "@/features/settings/stores";

export const useScrollLock = () => {
  const popupStore = usePopupStore();

  const isLocked = ref(false);

  const updateAppHeight = () => {
    const vh = window.innerHeight * 0.01;

    document.documentElement.style.setProperty("--app-height", `${vh * 100}px`);
  };

  const updateAppHeightAndLock = () => {
    updateAppHeight();

    if (isLocked.value) {
      unlockScroll();
      lockScroll();
    } else {
      unlockScroll();
    }
  };

  const lockScroll = () => {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: "smooth",
    });
    document.addEventListener("scroll", preventScroll, { passive: false });
    document.addEventListener("touchmove", preventScroll, { passive: false });
    document.addEventListener("wheel", preventScroll, { passive: false });
    document.body.style.position = "fixed";
    isLocked.value = true;
  };

  const unlockScroll = () => {
    document.removeEventListener("scroll", preventScroll);
    document.removeEventListener("touchmove", preventScroll);
    document.removeEventListener("wheel", preventScroll);
    document.body.style.position = "";
    isLocked.value = false;
  };

  const preventScroll = (e: Event) => {
    if (isLocked.value && !popupStore.isOpen) {
      e.preventDefault();
    }
  };

  const addResizeListeners = () => {
    window.addEventListener("resize", updateAppHeightAndLock);
    window.addEventListener("orientationchange", updateAppHeightAndLock);
  };

  const removeResizeListeners = () => {
    unlockScroll();
    window.removeEventListener("resize", updateAppHeightAndLock);
    window.removeEventListener("orientationchange", updateAppHeightAndLock);
  };

  const init = () => {
    updateAppHeight();
    addResizeListeners();
  };

  return {
    init,
    addResizeListeners,
    removeEventListener,
    unlockScroll,
    lockScroll,
    removeResizeListeners,
    updateAppHeightAndLock,
    updateAppHeight,
    isLocked,
  };
};
