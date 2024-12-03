import { ref, shallowRef } from "vue";
import type { ShallowRef } from "vue";
import { isNumber } from "@/util/guards";
import { useKeyboardHandlers } from "@/composables/useKeyboardHandlers";

export const inputHistoryDirectionByKey: { [key: string]: number } = {
  ArrowUp: -1,
  ArrowDown: 1,
};

export const useInputHistory = <Value>(initialValue?: Value) => {
  const inputHistory = ref<ShallowRef<Value[]>>(shallowRef([]));
  const currHistoryIdx = ref(0);
  const inputRef = ref<Value | undefined>(initialValue);

  const getNextOrPrevHistoryText = (n: number) => {
    if (!isNumber(currHistoryIdx.value) || !inputHistory.value) {
      return;
    }
    const len = inputHistory.value.length;
    if (!len) {
      return;
    }
    const maxIdx = inputHistory.value.length - 1;
    const incIdx = currHistoryIdx.value + n;
    const newIdx =
      incIdx >= 0 && incIdx <= maxIdx ? incIdx : n > 0 ? 0 : Math.abs(maxIdx);
    const newText = inputHistory.value[newIdx];
    if (newText) {
      (inputRef as ShallowRef<Value>).value = newText;
      currHistoryIdx.value = newIdx;
    }
  };

  const inputKeyHandlers = Object.entries(inputHistoryDirectionByKey).reduce(
    (acc, [key, arg]) => {
      acc[key] = () => {
        getNextOrPrevHistoryText(arg);
      };
      return acc;
    },
    {} as { [key: string]: Function },
  );

  const { handleKeyUp } = useKeyboardHandlers(inputKeyHandlers);

  return {
    inputRef,
    currHistoryIdx,
    inputHistory,
    handleKeyUp,
  };
};
