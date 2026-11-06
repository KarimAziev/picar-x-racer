// @vitest-environment jsdom

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useServoTuningStore } from "@/features/settings/stores/servoTuning";
import { useKeyboardControls } from "@/features/controller/composables/useKeyboardControls";
import { useControllerStore } from "@/features/controller/store";
import { usePopupStore, useSettingsStore } from "@/features/settings/stores";

describe("keyboard controls settings readiness", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("keeps the control loop idle while keybindings are unavailable", () => {
    const settingsStore = useSettingsStore();
    Reflect.deleteProperty(settingsStore.data, "keybindings");
    const controls = useKeyboardControls(
      useControllerStore(),
      settingsStore,
      usePopupStore(),
    );

    expect(() => controls.updateCarState()).not.toThrow();
  });
});

describe("servo keyboard tuning", () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });
  const setup = () => {
    const controller = useControllerStore();
    const settings = useSettingsStore();
    settings.data.keybindings = {
      left: ["a"],
      right: ["d"],
      decreaseCamPan: ["ArrowLeft"],
      increaseCamPan: ["ArrowRight"],
      accelerate: ["w"],
    };
    controller.calibrationMode = true;
    const controls = useKeyboardControls(controller, settings, usePopupStore());
    return { controller, settings, controls };
  };
  it("moves with plain keys and adjusts offsets with Shift", () => {
    const { controller, controls } = setup();
    const move = vi
      .spyOn(controller, "decreaseCamPan")
      .mockImplementation(() => {});
    const offset = vi
      .spyOn(controller, "decreaseCamPanCali")
      .mockImplementation(() => {});
    controls.handleKeyDown(
      new KeyboardEvent("keydown", { key: "ArrowLeft", code: "ArrowLeft" }),
    );
    controls.handleKeyDown(
      new KeyboardEvent("keydown", {
        key: "ArrowLeft",
        code: "ArrowLeft",
        shiftKey: true,
      }),
    );
    expect(move).toHaveBeenCalledTimes(1);
    expect(offset).toHaveBeenCalledTimes(1);
  });
  it("uses custom servo bindings and a configurable modifier", () => {
    const { controller, settings, controls } = setup();
    settings.data.keybindings.left = ["j"];
    useServoTuningStore().modifier = "altKey";
    const offset = vi
      .spyOn(controller, "decreaseServoDirCali")
      .mockImplementation(() => {});
    controls.handleKeyDown(
      new KeyboardEvent("keydown", { key: "j", code: "KeyJ", altKey: true }),
    );
    expect(offset).toHaveBeenCalledOnce();
  });
  it("handles uppercase Shift letters without invoking plain steering", () => {
    const { controller, controls } = setup();
    const offset = vi
      .spyOn(controller, "decreaseServoDirCali")
      .mockImplementation(() => {});
    const left = vi.spyOn(controller, "left").mockImplementation(() => {});
    controls.handleKeyDown(
      new KeyboardEvent("keydown", { key: "A", code: "KeyA", shiftKey: true }),
    );
    controls.updateCarState();
    expect(offset).toHaveBeenCalledOnce();
    expect(left).not.toHaveBeenCalled();
  });
  it("releases steering by physical key even when modifiers change", () => {
    const { controller, controls } = setup();
    const left = vi.spyOn(controller, "left").mockImplementation(() => {});
    const center = vi
      .spyOn(controller, "resetDirServoAngle")
      .mockImplementation(() => {});
    controls.handleKeyDown(
      new KeyboardEvent("keydown", { key: "a", code: "KeyA" }),
    );
    controls.updateCarState();
    controls.handleKeyUp(
      new KeyboardEvent("keyup", { key: "A", code: "KeyA", shiftKey: true }),
    );
    controls.updateCarState();
    expect(left).toHaveBeenCalledTimes(1);
    expect(center).not.toHaveBeenCalled();
  });
  it("does not move the robot when typing into tuning fields", () => {
    const { controller, controls } = setup();
    const move = vi
      .spyOn(controller, "decreaseCamPan")
      .mockImplementation(() => {});
    const input = document.createElement("input");
    input.addEventListener("keydown", controls.handleKeyDown);
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }));
    expect(move).not.toHaveBeenCalled();
  });
  it("does not accelerate while keyboard tuning is active", () => {
    const { controller, controls } = setup();
    const accelerate = vi
      .spyOn(controller, "accelerate")
      .mockImplementation(() => {});
    controls.handleKeyDown(
      new KeyboardEvent("keydown", { key: "w", code: "KeyW" }),
    );
    controls.updateCarState();
    expect(accelerate).not.toHaveBeenCalled();
  });
});
