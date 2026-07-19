// @vitest-environment jsdom

import PrimeVue from "primevue/config";
import { afterEach, describe, expect, it } from "vitest";
import { createApp, h, nextTick, ref, type App } from "vue";
import NumberField from "@/ui/NumberField.vue";

const mountedApps: App[] = [];

afterEach(() => {
  mountedApps.splice(0).forEach((app) => app.unmount());
});

const mountNumberField = (editable?: boolean) => {
  const container = document.createElement("div");
  const value = ref(0.1);
  const app = createApp({
    setup: () => () =>
      h(NumberField, {
        editable,
        field: "confidence",
        modelValue: value.value,
        min: 0,
        max: 1,
        step: 0.1,
        normalizeValue: (newValue: number) => Math.round(newValue * 10) / 10,
        "onUpdate:modelValue": (newValue: number | null) => {
          value.value = newValue ?? 0;
        },
      }),
  });

  app.use(PrimeVue);
  app.directive("tooltip", {});
  app.mount(container);
  mountedApps.push(app);

  return { container, value };
};

describe("NumberField", () => {
  it("keeps the non-input implementation by default", () => {
    const { container } = mountNumberField();

    expect(container.querySelector("input")).toBeNull();
    expect(container.querySelector(".wrapper")?.textContent).toContain("0.1");
  });

  it("renders an editable PrimeVue number input when enabled", async () => {
    const { container, value } = mountNumberField(true);
    const input = container.querySelector<HTMLInputElement>(
      "input#confidence[role='spinbutton']",
    );

    expect(input).not.toBeNull();
    expect(input?.value).toBe("0.1");

    const incrementButton = container.querySelector<HTMLButtonElement>(
      ".p-inputnumber-increment-button",
    );
    incrementButton?.dispatchEvent(
      new MouseEvent("mousedown", { bubbles: true }),
    );
    incrementButton?.dispatchEvent(
      new MouseEvent("mouseup", { bubbles: true }),
    );
    await nextTick();

    expect(value.value).toBe(0.2);
    expect(input?.value).toBe("0.2");
  });
});
