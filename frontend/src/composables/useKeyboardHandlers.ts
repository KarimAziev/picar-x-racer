import { formatKeyEventItem } from "@/util/keyboard-util";

export const useKeyboardHandlers = (keyHandlers: {
  [key: string]: Function;
}) => {
  const handleKeyUp = (event: KeyboardEvent) => {
    const key = formatKeyEventItem(event);
    if (keyHandlers[key]) {
      keyHandlers[key]();
    }
  };

  const addKeyEventListeners = () => {
    window.addEventListener("keyup", handleKeyUp);
  };

  const removeKeyEventListeners = () => {
    window.removeEventListener("keyup", handleKeyUp);
  };

  return {
    addKeyEventListeners,
    removeKeyEventListeners,
    handleKeyUp,
  };
};
