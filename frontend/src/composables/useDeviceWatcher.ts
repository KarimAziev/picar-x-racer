import { ref, onBeforeUnmount, onMounted } from "vue";

export const useDeviceWatcher = () => {
  const re =
    /Mobi|Android|iPad|iPhone|SAMSUNG|SGH-[I|N|T]|GT-[I|P|N]|SM-[N|P|T|Z|G]|SHV-E|SCH-[I|J|R|S]|SPH-L/i;
  const isMobile = ref(re.test(navigator.userAgent));

  const updateDeviceStatus = () => {
    isMobile.value = re.test(navigator.userAgent);
  };

  onMounted(() => {
    window.addEventListener("resize", updateDeviceStatus);
    window.addEventListener("orientationchange", updateDeviceStatus);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", updateDeviceStatus);
    window.removeEventListener("orientationchange", updateDeviceStatus);
  });

  return isMobile;
};
