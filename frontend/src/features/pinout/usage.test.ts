// @vitest-environment jsdom

import { describe, expect, it } from "vitest";
import type { JSONSchema } from "@/ui/JsonSchema/interface";
import { collectPinAssignments } from "./usage";
import { gpioForPin, groupPinAssignments, normalizePins } from "./util";

const pin: JSONSchema = {
  title: "GPIO pin",
  "x-ui-type": "pin",
  anyOf: [{ type: "integer" }, { type: "string" }, { type: "null" }],
};

const schema: JSONSchema = {
  type: "object",
  properties: {
    motors: {
      type: "array",
      title: "Motors",
      props: { itemLabel: "Motor" },
      items: {
        anyOf: [
          { $ref: "#/$defs/GPIOMotor" },
          { $ref: "#/$defs/I2CMotor" },
          { $ref: "#/$defs/PhaseMotor" },
        ],
      },
    },
    servo: {
      title: "Steering servo",
      anyOf: [{ $ref: "#/$defs/GPIOServo" }, { $ref: "#/$defs/I2CServo" }],
    },
    led: {
      title: "LED",
      anyOf: [{ $ref: "#/$defs/GPIOServo" }, { type: "null" }],
    },
    ultrasonic: {
      type: "object",
      title: "Distance sensor",
      properties: { trig_pin: pin, echo_pin: pin },
    },
    encoder: {
      type: "object",
      title: "Wheel encoders",
      properties: {
        enabled: { type: "boolean" },
        sensors: {
          type: "array",
          title: "Sensors",
          items: {
            discriminator: {
              propertyName: "driver",
              mapping: {
                gpio: "#/$defs/GPIOEncoder",
                mock: "#/$defs/MockEncoder",
              },
            },
            oneOf: [
              { $ref: "#/$defs/GPIOEncoder" },
              { $ref: "#/$defs/MockEncoder" },
            ],
          },
        },
      },
    },
  },
  $defs: {
    GPIOMotor: {
      type: "object",
      properties: { forward_pin: pin, backward_pin: pin, enable_pin: pin },
    },
    I2CMotor: {
      type: "object",
      properties: {
        dir_pin: pin,
        channel: { "x-ui-type": "string_or_number" },
      },
    },
    PhaseMotor: {
      type: "object",
      properties: { phase_pin: pin, enable_pin: pin },
    },
    GPIOServo: { type: "object", properties: { pin } },
    I2CServo: {
      type: "object",
      properties: { channel: { type: "integer" }, driver: { type: "object" } },
    },
    GPIOEncoder: {
      type: "object",
      properties: { driver: { const: "gpio" }, a_pin: pin, b_pin: pin },
    },
    MockEncoder: { type: "object", properties: { driver: { const: "mock" } } },
  },
};

describe("configuration GPIO assignments", () => {
  it("labels enabled, disabled and on-demand components without assuming live activity", () => {
    const assignments = collectPinAssignments(schema, {
      motors: [
        {
          name: "Drive",
          enabled: true,
          forward_pin: "GPIO20",
          backward_pin: 21,
          enable_pin: 26,
        },
      ],
      servo: { name: "Steering", enabled: false, pin: "BOARD11" },
      led: { name: "Status light", pin: 26 },
      ultrasonic: { trig_pin: "D2", echo_pin: "D14" },
    });

    expect(assignments).toHaveLength(7);
    expect(assignments[2]).toEqual({
      key: '["motors",0,"enable_pin"]',
      owner: "Motors · Drive",
      field: "GPIO pin",
      value: 26,
      state: "enabled",
    });
    expect(assignments[3]).toMatchObject({
      owner: "Steering",
      state: "disabled",
    });
    expect(assignments[4]).toMatchObject({
      owner: "Status light",
      state: "configured",
    });
    expect(assignments[5]).toMatchObject({
      owner: "Distance sensor",
      state: "configured",
    });
  });

  it("includes GPIO direction pins but excludes I²C channels and addresses", () => {
    const assignments = collectPinAssignments(schema, {
      motors: [
        {
          dir_pin: 23,
          channel: 11,
          driver: { address: 64, bus: 1 },
          enabled: true,
        },
      ],
      servo: { channel: 11, driver: { address: 65, bus: 1 }, enabled: true },
    });
    expect(assignments).toEqual([
      {
        key: '["motors",0,"dir_pin"]',
        owner: "Motors · Motor 1",
        field: "GPIO pin",
        value: 23,
        state: "enabled",
      },
    ]);
  });

  it("handles phase motors and omits null, missing and non-pin values", () => {
    const assignments = collectPinAssignments(schema, {
      motors: [
        { phase_pin: 24, enable_pin: 25, enabled: false },
        { forward_pin: 20, backward_pin: false, enable_pin: null },
      ],
      led: null,
    });
    expect(assignments.map(({ value }) => value)).toEqual([24, 25, 20]);
    expect(assignments[0].state).toBe("disabled");
    expect(collectPinAssignments(null, {})).toEqual([]);
    expect(collectPinAssignments(schema, null)).toEqual([]);
  });

  it("inherits a disabled parent and honors the selected discriminated sensor", () => {
    const assignments = collectPinAssignments(schema, {
      encoder: {
        enabled: false,
        sensors: [
          { driver: "gpio", a_pin: 5, b_pin: 6, enabled: true },
          { driver: "mock", a_pin: 7, b_pin: 8 },
        ],
      },
    });
    expect(assignments.map(({ value, state }) => [value, state])).toEqual([
      [5, "disabled"],
      [6, "disabled"],
    ]);
    expect(assignments[0].owner).toBe("Wheel encoders · Sensors · Item 1");
  });

  it("reflects edited pins, names, enable flags, driver changes and removed items", () => {
    const model = {
      motors: [{ dir_pin: 23, channel: 0, name: "Drive", enabled: true }],
    };
    const saved = structuredClone(model);
    model.motors[0].dir_pin = 26;
    model.motors[0].name = "Rear motor";
    model.motors[0].enabled = false;
    expect(collectPinAssignments(schema, model)[0]).toMatchObject({
      value: 26,
      owner: "Motors · Rear motor",
      state: "disabled",
    });
    expect(collectPinAssignments(schema, saved)[0]).toMatchObject({
      value: 23,
      state: "enabled",
    });
    model.motors.splice(0);
    expect(collectPinAssignments(schema, model)).toEqual([]);
  });

  it("groups aliases by physical GPIO and preserves all owners, including disabled owners", () => {
    const { hash } = normalizePins({
      J8: {
        name: "J8",
        columns: 2,
        rows: 20,
        pins: {
          "37": {
            name: "GPIO26",
            gpio_number: 26,
            number: 37,
            row: 19,
            col: 1,
            names: ["GPIO26", "BCM26", "BOARD37", "J8:37", "D14"],
            interfaces: ["gpio"],
          },
        },
      },
    });
    const assignments = collectPinAssignments(schema, {
      motors: [
        {
          name: "Drive",
          enabled: true,
          forward_pin: "BCM26",
          backward_pin: "BOARD37",
          enable_pin: "J8:37",
        },
      ],
      servo: { pin: "D14", enabled: false },
      led: { pin: 26 },
      ultrasonic: { trig_pin: "unknown", echo_pin: null },
    });
    const grouped = groupPinAssignments(assignments, hash);
    expect(gpioForPin("26", hash)).toBe(26);
    expect(gpioForPin(26, hash)).toBe(26);
    expect(gpioForPin("gpio26", hash)).toBeUndefined();
    expect(gpioForPin("026", hash)).toBeUndefined();
    expect([...grouped.keys()]).toEqual([26]);
    expect(grouped.get(26)).toHaveLength(5);
    expect(grouped.get(26)?.map(({ state }) => state)).toEqual([
      "enabled",
      "enabled",
      "enabled",
      "disabled",
      "configured",
    ]);
  });
});
