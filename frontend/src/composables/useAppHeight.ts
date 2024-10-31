import { useWindowSize } from "@/composables/useWindowSize";

import { watch, onMounted } from "vue";

export const useAppHeight = () => {
  const { height } = useWindowSize();

  const updateAppHeight = (newValue: number) => {
    const vh = newValue * 0.01;
    const appHeight = vh * 100;

    document.documentElement.style.setProperty(
      "--app-height",
      `${appHeight}px`,
    );
  };
  watch(() => height.value, updateAppHeight);
  onMounted(() => updateAppHeight(height.value));
};
