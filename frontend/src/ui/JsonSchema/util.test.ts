// @vitest-environment jsdom

import { describe, expect, it } from "vitest";
import type { JSONSchema } from "@/ui/JsonSchema/interface";
import { detectCandidateIndex, validateAll } from "@/ui/JsonSchema/util";

const gpioMotor: JSONSchema = {
  type: "object",
  required: ["forward_pin"],
  properties: {
    forward_pin: { type: "pin" },
    name: { type: "string", shared: true },
  },
};

const i2cMotor: JSONSchema = {
  type: "object",
  required: ["channel"],
  properties: {
    channel: { type: "string_or_number" },
    name: { type: "string", shared: true },
  },
};

const motorsSchema: JSONSchema = {
  type: "array",
  minItems: 1,
  maxItems: 2,
  items: { anyOf: [gpioMotor, i2cMotor] },
};

describe("polymorphic array schemas", () => {
  it("detects the hardware type independently for each item", () => {
    const options = [gpioMotor, i2cMotor];

    expect(detectCandidateIndex({ forward_pin: 6 }, options)).toBe(0);
    expect(detectCandidateIndex({ channel: "P12" }, options)).toBe(1);
  });

  it("validates each item against its detected hardware type", () => {
    expect(
      validateAll(motorsSchema, [
        { forward_pin: 6, name: "left" },
        { channel: "P12", name: "right" },
      ]),
    ).toBeNull();
  });

  it("enforces the configured item count", () => {
    expect(validateAll(motorsSchema, [])).toBe("Add at least 1 item.");
    expect(
      validateAll(motorsSchema, [
        { forward_pin: 6 },
        { forward_pin: 13 },
        { forward_pin: 20 },
      ]),
    ).toBe("No more than 2 items are allowed.");
  });

  it("enforces a schema-defined unique item property", () => {
    expect(
      validateAll({ ...motorsSchema, uniqueItemProperty: "name" }, [
        { forward_pin: 6, name: "Main" },
        { channel: "P12", name: " main " },
      ]),
    ).toBe("Name values must be unique.");
  });
});
