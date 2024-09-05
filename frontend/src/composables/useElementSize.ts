import { onMounted, onBeforeUnmount, reactive, type Ref } from "vue";

export const useElementSize = (elementRef: Ref<HTMLElement | null>) => {
  const size = reactive({
    width: 0,
    height: 0,
  });

  const updateSize = (entries: ResizeObserverEntry[]) => {
    if (entries.length === 0) {
      return;
    }
    const entry = entries[0];
    size.width = entry.contentRect.width;
    size.height = entry.contentRect.height;
  };

  let resizeObserver: ResizeObserver | null = null;

  onMounted(() => {
    if (elementRef.value) {
      resizeObserver = new ResizeObserver((entries) => updateSize(entries));
      resizeObserver.observe(elementRef.value);
      const rect = elementRef.value.getBoundingClientRect();
      size.width = rect.width;
      size.height = rect.height;
    }
  });

  onBeforeUnmount(() => {
    if (resizeObserver && elementRef.value) {
      resizeObserver.unobserve(elementRef.value);
    }
  });

  return size;
};
