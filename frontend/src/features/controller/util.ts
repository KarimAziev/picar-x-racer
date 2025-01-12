import { keyboardInputID } from "@/features/controller/config";

export const focusToKeyboardHandler = () => {
  const elem = document.querySelector<HTMLInputElement>(`#${keyboardInputID}`);
  if (elem && document.activeElement !== elem) {
    elem.focus();
    return document.activeElement === elem;
  }
};
