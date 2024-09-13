import { ref } from "vue";

export function useAsyncDebounce<T extends (...args: any[]) => Promise<void>>(
  func: T,
  waitFor: number,
): (...args: Parameters<T>) => void {
  const timeout = ref<NodeJS.Timeout>();

  return async (...args: Parameters<T>) => {
    let later = async () => {
      if (timeout.value) {
        clearTimeout(timeout.value);
      }

      await func(...args);
    };
    if (timeout.value) {
      clearTimeout(timeout.value);
    }

    timeout.value = setTimeout(later, waitFor);
  };
}
