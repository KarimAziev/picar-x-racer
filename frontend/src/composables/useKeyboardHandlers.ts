import { formatKeyEventItem } from "@/util/keyboard-util";

export const useKeyboardHandlers = (
  keyHandlers: {
    [key: string]: Function;
  },
  target?: HTMLElement,
) => {
  const handleKeyUp = (event: Event) => {
    const key = formatKeyEventItem(event as KeyboardEvent);
    if (keyHandlers[key]) {
      keyHandlers[key]();
    }
  };

  const addKeyEventListeners = () => {
    (target || window).addEventListener("keyup", handleKeyUp);
  };

  const removeKeyEventListeners = () => {
    (target || window).removeEventListener("keyup", handleKeyUp);
  };

  return {
    addKeyEventListeners,
    removeKeyEventListeners,
    handleKeyUp,
  };
};
