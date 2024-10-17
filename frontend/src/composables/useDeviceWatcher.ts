import { ref, onUnmounted, onMounted } from "vue";

export const useDeviceWatcher = () => {
  const isMobile = ref(/Mobi|Android|iPhone/i.test(navigator.userAgent));

  const updateDeviceStatus = () => {
    isMobile.value = /Mobi|Android|iPhone/i.test(navigator.userAgent);
  };

  onMounted(() => {
    window.addEventListener("resize", updateDeviceStatus);
    window.addEventListener("orientationchange", updateDeviceStatus);
  });

  onUnmounted(() => {
    window.removeEventListener("resize", updateDeviceStatus);
    window.removeEventListener("orientationchange", updateDeviceStatus);
  });

  return isMobile;
};
