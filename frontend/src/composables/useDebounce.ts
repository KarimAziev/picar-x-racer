import { ref, onBeforeUnmount } from "vue";

export function useAsyncDebounce<T extends (...args: any[]) => Promise<void>>(
  func: T,
  waitFor: number,
) {
  const timeout = ref<NodeJS.Timeout>();

  onBeforeUnmount(() => {
    if (timeout.value) {
      clearTimeout(timeout.value);
    }
  });

  return async (...args: Parameters<T>) => {
    let later = async () => {
      if (timeout.value) {
        clearTimeout(timeout.value);
      }

      return await func(...args);
    };
    if (timeout.value) {
      clearTimeout(timeout.value);
    }

    timeout.value = setTimeout(later, waitFor);
  };
}

export function useDebounce<T extends (...args: any[]) => any>(
  func: T,
  waitFor: number,
) {
  const timeout = ref<NodeJS.Timeout>();

  onBeforeUnmount(() => {
    if (timeout.value) {
      clearTimeout(timeout.value);
    }
  });

  return (...args: Parameters<T>) => {
    let later = () => {
      if (timeout.value) {
        clearTimeout(timeout.value);
      }

      return func(...args);
    };
    if (timeout.value) {
      clearTimeout(timeout.value);
    }

    timeout.value = setTimeout(later, waitFor);
  };
}
