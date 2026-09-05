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

const mountSensorArray = () => {
  const container = document.createElement("div");
  const model = {
    sensors: [{ driver: "temperature", name: "Cabin temperature" }],
  };
  const schema: JSONSchemaType = {
    type: "array",
    title: "Sensors",
    props: { typeLabel: "Sensor type" },
    items: {
      discriminator: {
        propertyName: "driver",
        mapping: {
          temperature: "#/$defs/TemperatureSensor",
          pressure: "#/$defs/PressureSensor",
        },
      },
      oneOf: [
        { $ref: "#/$defs/TemperatureSensor" },
        { $ref: "#/$defs/PressureSensor" },
      ],
    },
  };
  const defs: Record<string, JSONSchemaType> = {
    TemperatureSensor: {
      type: "object",
      title: "Temperature sensor",
      properties: {
        driver: {
          type: "string",
          title: "Driver",
          const: "temperature",
        },
        name: { type: "string", title: "Name", default: "Temperature" },
      },
    },
    PressureSensor: {
      type: "object",
      title: "Pressure sensor",
      properties: {
        driver: { type: "string", title: "Driver", const: "pressure" },
        name: { type: "string", title: "Name", default: "Pressure" },
      },
    },
  };
  const pinia = createPinia();
  const app = createApp({
    setup: () => () =>
      h(JsonSchema, {
        schema,
        defs,
        model,
        origModel: structuredClone(model),
        path: ["sensors"],
        idPrefix: "test-sensors",
        level: 0,
        collapsed: false,
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

  it("renders a discriminated oneOf array item with one type selector", async () => {
    const container = mountSensorArray();
    await nextTick();

    expect(container.querySelectorAll('[data-pc-name="select"]')).toHaveLength(
      1,
    );
    expect(container.textContent).toContain("Temperature Sensor");
    expect(container.textContent).toContain("Sensor type");
    expect(container.textContent).toContain("Cabin temperature");
    expect(container.textContent).not.toContain("Driver");
  });
});
