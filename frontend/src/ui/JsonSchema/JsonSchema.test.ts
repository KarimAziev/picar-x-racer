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

const mountSchema = (
  schema: JSONSchemaType,
  value: unknown,
  defs?: Record<string, JSONSchemaType>,
) => {
  const container = document.createElement("div");
  const model = { pin: value };
  const pinia = createPinia();
  usePinoutStore(pinia).loaded = true;
  const app = createApp({
    setup: () => () =>
      h(JsonSchema, {
        schema,
        defs,
        model,
        origModel: { ...model },
        path: ["pin"],
        idPrefix: "test-pin",
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

describe("JsonSchema nested layout", () => {
  it("gives nested objects, arrays and selected variants full-width sections", async () => {
    const container = mountSchema(
      {
        type: "object",
        title: "Hardware",
        properties: {
          encoders: {
            type: "object",
            title: "Drive encoders",
            properties: {
              frequency: { type: "number", title: "Sample frequency" },
              devices: {
                type: "array",
                title: "Devices",
                items: { $ref: "#/$defs/Encoder" },
              },
            },
          },
          steering: {
            title: "Steering sensor",
            anyOf: [{ $ref: "#/$defs/Encoder" }, { type: "null" }],
          },
        },
      },
      {
        encoders: { frequency: 100, devices: [{ enabled: true, ticks: 160 }] },
        steering: { enabled: true, ticks: 8 },
      },
      {
        Encoder: {
          type: "object",
          title: "Mock encoder",
          properties: {
            enabled: { type: "boolean", title: "Enabled" },
            ticks: { type: "integer", title: "Ticks per sample" },
          },
        },
      },
    );
    await nextTick();

    const grids = container.querySelectorAll(".schema-grid");
    expect(grids).toHaveLength(5);
    const sections = container.querySelectorAll(".schema-section");
    expect(sections).toHaveLength(6);
    sections.forEach((section) => {
      expect(section.classList.contains("col-span-full")).toBe(true);
    });

    const fieldsets = container.querySelectorAll("fieldset");
    expect(fieldsets).toHaveLength(4);
    expect(fieldsets[0].classList.contains("schema-section-flat")).toBe(false);
    expect(fieldsets[1].classList.contains("schema-section-flat")).toBe(false);
    expect(fieldsets[2].classList.contains("schema-section-flat")).toBe(true);
    expect(container.textContent).toContain("Ticks per sample");
    expect(container.querySelector('[aria-label="Remove item"]')).not.toBeNull();
  });

  it("keeps deeply nested sections collapsible and their fields editable", async () => {
    const value = { sensor: { calibration: { name: "Center" } } };
    const container = mountSchema(
      {
        type: "object",
        properties: {
          sensor: {
            type: "object",
            title: "Sensor",
            properties: {
              calibration: {
                type: "object",
                title: "Calibration",
                properties: { name: { type: "string", title: "Name" } },
              },
            },
          },
        },
      },
      value,
    );
    await nextTick();

    const section = container.querySelector(".schema-section-flat")!;
    const toggle = section.querySelector<HTMLButtonElement>("legend button")!;
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    toggle.click();
    await nextTick();
    expect(toggle.getAttribute("aria-expanded")).toBe("true");

    const input = section.querySelector<HTMLInputElement>("input")!;
    input.value = "Straight ahead";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await nextTick();
    expect(value.sensor.calibration.name).toBe("Straight ahead");

    toggle.click();
    await nextTick();
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(value.sensor.calibration.name).toBe("Straight ahead");
  });
});
