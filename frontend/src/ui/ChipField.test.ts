// @vitest-environment jsdom

import PrimeVue from "primevue/config";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";
import { createApp, h, nextTick, ref, type App } from "vue";
import { usePopupStore } from "@/features/settings/stores";
import ChipField from "@/ui/ChipField.vue";

const mountedApps: { app: App; container: HTMLElement }[] = [];

afterEach(() => {
  mountedApps.splice(0).forEach(({ app, container }) => {
    app.unmount();
    container.remove();
  });
});

const mountChipField = () => {
  const container = document.createElement("div");
  const value = ref<string[]>([]);
  const app = createApp({
    setup: () => () =>
      h(ChipField, {
        field: "labels",
        modelValue: value.value,
        suggestions: ["person", "car", "sports ball"],
        "onUpdate:modelValue": (newValue: string[]) => {
          value.value = newValue;
        },
      }),
  });

  document.body.append(container);
  const pinia = createPinia();
  app.use(pinia);
  app.use(PrimeVue, { unstyled: true });
  app.directive("tooltip", {});
  app.mount(container);
  mountedApps.push({ app, container });

  return { container, popupStore: usePopupStore(pinia), value };
};

const dispatchKey = (key: string, options: KeyboardEventInit = {}) => {
  const event = new KeyboardEvent("keydown", {
    key,
    code: key,
    bubbles: true,
    cancelable: true,
    ...options,
  });
  window.dispatchEvent(event);
  return event;
};

const waitForPopover = async () => {
  await nextTick();
  await new Promise((resolve) => window.setTimeout(resolve, 50));
};

describe("ChipField keyboard navigation", () => {
  it("keeps Enter entry for the focused text input", async () => {
    const { container, value } = mountChipField();
    const input = container.querySelector<HTMLInputElement>("#labels")!;

    input.focus();
    await waitForPopover();
    input.value = "robot";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await nextTick();

    dispatchKey("Enter");
    await nextTick();

    expect(value.value).toEqual(["robot"]);
    expect(input.value).toBe("");
  });

  it("navigates, selects, and closes with the TreeSelect keymap", async () => {
    const { container, popupStore, value } = mountChipField();
    const input = container.querySelector<HTMLInputElement>("#labels")!;

    input.focus();
    await waitForPopover();
    expect(popupStore.isEscapable).toBe(false);

    const event = dispatchKey("n", { code: "KeyN", ctrlKey: true });
    await nextTick();
    expect(event.defaultPrevented).toBe(true);
    expect(document.activeElement?.getAttribute("aria-label")).toBe(
      "Add person",
    );

    dispatchKey("ArrowDown");
    await nextTick();
    expect(document.activeElement?.getAttribute("aria-label")).toBe("Add car");

    dispatchKey("p", { code: "KeyP", ctrlKey: true });
    await nextTick();
    expect(document.activeElement?.getAttribute("aria-label")).toBe(
      "Add person",
    );

    dispatchKey("n", { code: "KeyN", ctrlKey: true });
    await nextTick();
    expect(document.activeElement?.getAttribute("aria-label")).toBe("Add car");

    dispatchKey("g", { code: "KeyG", ctrlKey: true });
    await nextTick();
    expect(popupStore.isEscapable).toBe(true);
    expect(document.activeElement).toBe(input);

    const closedEvent = dispatchKey("ArrowDown");
    await nextTick();
    expect(closedEvent.defaultPrevented).toBe(false);
    expect(document.activeElement).toBe(input);

    input.click();
    await waitForPopover();
    dispatchKey("v", { code: "KeyV", ctrlKey: true });
    await nextTick();
    expect(document.activeElement?.getAttribute("aria-label")).toBe(
      "Add sports ball",
    );

    dispatchKey("v", { code: "KeyV", altKey: true });
    await nextTick();
    expect(document.activeElement?.getAttribute("aria-label")).toBe(
      "Add person",
    );

    dispatchKey("ArrowDown");
    await nextTick();
    dispatchKey("Enter");
    await nextTick();
    expect(value.value).toEqual(["car"]);
    expect(document.activeElement).toBe(input);

    dispatchKey("Escape");
    await nextTick();
    expect(popupStore.isEscapable).toBe(true);
    expect(document.activeElement).toBe(input);
  });
});
