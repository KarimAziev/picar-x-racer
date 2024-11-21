import { ref, shallowRef } from "vue";
import type { ShallowRef } from "vue";
import { isNumber } from "@/util/guards";
import { useKeyboardHandlers } from "@/composables/useKeyboardHandlers";

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

  const setNextHistoryText = () => {
    getNextOrPrevHistoryText(1);
  };

  const setPrevHistoryText = () => {
    getNextOrPrevHistoryText(-1);
  };

  const inputKeyHandlers: { [key: string]: Function } = {
    ArrowUp: setPrevHistoryText,
    ArrowDown: setNextHistoryText,
  };

  const { handleKeyUp } = useKeyboardHandlers(inputKeyHandlers);

  return {
    inputRef,
    currHistoryIdx,
    inputHistory,
    handleKeyUp,
  };
};
