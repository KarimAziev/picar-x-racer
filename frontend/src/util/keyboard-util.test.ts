import { describe, expect, it } from "vitest";
import { formatKeyboardEvents, parseKeySequence } from "@/util/keyboard-util";
describe("shortcut modifier formatting", () => {
  it.each([
    "Shift-ArrowLeft",
    "Meta-ArrowRight",
    "Ctrl-Alt-a",
    "A",
    "ArrowLeft",
  ])("round trips %s", (shortcut) => {
    expect(formatKeyboardEvents(parseKeySequence(shortcut))).toBe(shortcut);
  });
});
