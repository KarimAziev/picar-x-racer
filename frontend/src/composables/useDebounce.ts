import { ref, onBeforeUnmount } from "vue";

export function useAsyncDebounce<T extends (...args: any[]) => Promise<any>>(
  func: T,
  waitFor: number,
): (...args: Parameters<T>) => Promise<ReturnType<T>> {
  const timeout = ref<NodeJS.Timeout>();
  onBeforeUnmount(() => {
    if (timeout.value) {
      clearTimeout(timeout.value);
    }
  });

  return async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    if (timeout.value) {
      clearTimeout(timeout.value);
    }

    return new Promise((resolve, rej) => {
      timeout.value = setTimeout(async () => {
        try {
          const result = await func(...args);
          resolve(result);
        } catch (error) {
          rej();
        }
      }, waitFor);
    });
  };
}
