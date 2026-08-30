// @vitest-environment jsdom

import PrimeVue from "primevue/config";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";
import { createApp, h, nextTick, type App } from "vue";
import { useStore as usePinoutStore } from "@/features/pinout/store";
import JsonSchema from "@/ui/JsonSchema/JsonSchema.vue";
import type { JSONSchema as JSONSchemaType } from "@/ui/JsonSchema/interface";

const mountedApps: { app: App; container: HTMLElement }[] = [];

afterEach(() => {
  mountedApps.splice(0).forEach(({ app, container }) => {
    app.unmount();
    container.remove();
  });
});

const mountSchema = (schema: JSONSchemaType, value: string | number) => {
  const container = document.createElement("div");
  const model = { pin: value };
  const pinia = createPinia();
  usePinoutStore(pinia).loaded = true;
  const app = createApp({
    setup: () => () =>
      h(JsonSchema, {
        schema,
        model,
        origModel: { ...model },
        path: ["pin"],
        idPrefix: "test-pin",
        level: 0,
      }),
  });

  document.body.append(container);
  app.use(pinia);
  app.use(PrimeVue, { unstyled: true });
  app.directive("tooltip", {});
  app.mount(container);
  mountedApps.push({ app, container });
  return container;
};

describe("JsonSchema custom union rendering", () => {
  it("renders a pin chooser instead of a union branch selector", async () => {
    const container = mountSchema(
      {
        anyOf: [{ type: "string" }, { type: "integer" }],
        default: 26,
        title: "Pin",
        "x-ui-type": "pin",
      },
      26,
    );
    await nextTick();

    expect(container.textContent).toContain("Pin");
    expect(container.textContent).toContain("26");
    expect(container.textContent).not.toContain("String");
    expect(container.textContent).not.toContain("Integer");
    expect(container.querySelector("button")).not.toBeNull();
    expect(container.querySelector(".p-select")).toBeNull();
  });
});
