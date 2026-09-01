// @vitest-environment jsdom

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
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
