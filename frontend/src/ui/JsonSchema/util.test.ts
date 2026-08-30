// @vitest-environment jsdom

import { describe, expect, it } from "vitest";
import type { JSONSchema } from "@/ui/JsonSchema/interface";
import { componentsWithDefaults } from "@/ui/JsonSchema/config";
import {
  detectCandidateIndex,
  getDirectSchemaTypes,
  getComponentWithProps,
  getFieldType,
  getSchemaTypes,
  hasDirectSchemaType,
  resolveRef,
  schemaAllowsType,
  validateAll,
} from "@/ui/JsonSchema/util";

const gpioMotor: JSONSchema = {
  type: "object",
  required: ["forward_pin"],
  properties: {
    forward_pin: { type: "integer", "x-ui-type": "pin" },
    name: { type: "string", shared: true },
  },
};

const i2cMotor: JSONSchema = {
  type: "object",
  required: ["channel"],
  properties: {
    channel: { type: "string", "x-ui-type": "string_or_number" },
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
  it("selects widgets from OpenAPI extension metadata", () => {
    const component = getComponentWithProps({
      type: "integer",
      "x-ui-type": "pin",
    });

    expect(component?.comp).toBe(componentsWithDefaults.pin.comp);
  });

  it("selects a custom widget when value types are declared by anyOf", () => {
    const component = getComponentWithProps({
      anyOf: [{ type: "string" }, { type: "integer" }],
      "x-ui-type": "pin",
    });

    expect(component?.comp).toBe(componentsWithDefaults.pin.comp);
  });

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

describe("schema type resolution", () => {
  it("keeps structural, value, and UI field types separate", () => {
    const schema: JSONSchema = {
      anyOf: [{ type: "string" }, { type: "integer" }],
      "x-ui-type": "string_or_number",
    };

    expect(getDirectSchemaTypes(schema)).toEqual([]);
    expect(getSchemaTypes(schema)).toEqual(["string", "integer"]);
    expect(getFieldType(schema)).toBe("string_or_number");
    expect(hasDirectSchemaType(schema, "string")).toBe(false);
    expect(schemaAllowsType(schema, "string")).toBe(true);
  });

  it("supports JSON Schema type arrays", () => {
    const schema: JSONSchema = { type: ["string", "null"] };

    expect(getDirectSchemaTypes(schema)).toEqual(["string", "null"]);
    expect(schemaAllowsType(schema, "null")).toBe(true);
    expect(getFieldType(schema)).toBe("string");
  });

  it("preserves UI metadata alongside a resolved reference", () => {
    const resolved = resolveRef(
      { $ref: "#/$defs/PinValue", "x-ui-type": "pin" },
      {
        PinValue: {
          anyOf: [{ type: "string" }, { type: "integer" }],
        },
      },
    );

    expect(resolved?.$ref).toBeUndefined();
    expect(resolved?.["x-ui-type"]).toBe("pin");
    expect(getSchemaTypes(resolved)).toEqual(["string", "integer"]);
  });

  it("infers object and array structure from their schema keywords", () => {
    expect(hasDirectSchemaType({ properties: {} }, "object")).toBe(true);
    expect(hasDirectSchemaType({ items: { type: "string" } }, "array")).toBe(
      true,
    );
  });
});

describe("field component resolution", () => {
  it.each([
    ["pin", componentsWithDefaults.pin.comp],
    ["hex", componentsWithDefaults.hex.comp],
    ["string_or_number", componentsWithDefaults.string_or_number.comp],
  ] as const)("renders union-backed %s widgets", (fieldType, component) => {
    expect(
      getComponentWithProps({
        anyOf: [{ type: "integer" }, { type: "string" }],
        "x-ui-type": fieldType,
      })?.comp,
    ).toBe(component);
  });

  it.each([
    ["motor_direction", "integer", componentsWithDefaults.motor_direction.comp],
    [
      "calibration_offset",
      "number",
      componentsWithDefaults.calibration_offset.comp,
    ],
    ["select", "integer", componentsWithDefaults.select.comp],
  ] as const)("renders direct %s widgets", (fieldType, type, component) => {
    expect(
      getComponentWithProps({
        type,
        "x-ui-type": fieldType,
        props: fieldType === "select" ? { options: [] } : undefined,
      })?.comp,
    ).toBe(component);
  });

  it.each([
    ["integer", componentsWithDefaults.integer.comp],
    ["number", componentsWithDefaults.number.comp],
    ["string", componentsWithDefaults.string.comp],
    ["boolean", componentsWithDefaults.boolean.comp],
  ] as const)(
    "renders ordinary %s fields without x-ui-type",
    (type, component) => {
      expect(getComponentWithProps({ type })?.comp).toBe(component);
    },
  );

  it("uses a select for an ordinary integer enum", () => {
    const component = getComponentWithProps({
      type: "integer",
      enum: [1, 2],
    });

    expect(component?.comp).toBe(componentsWithDefaults.select.comp);
    expect(component?.props.options).toEqual([
      { value: 1, label: "1" },
      { value: 2, label: "2" },
    ]);
  });

  it("does not turn structural or ambiguous union schemas into fields", () => {
    expect(getComponentWithProps({ type: "object", properties: {} })).toBe(
      undefined,
    );
    expect(
      getComponentWithProps({
        anyOf: [{ type: "integer" }, { type: "string" }],
      }),
    ).toBe(undefined);
  });
});

describe("custom union validation", () => {
  const pinSchema: JSONSchema = {
    anyOf: [{ type: "string" }, { type: "integer" }],
    "x-ui-type": "pin",
  };

  it("accepts either supported pin representation", () => {
    expect(validateAll(pinSchema, "GPIO26")).toBeNull();
    expect(validateAll(pinSchema, 26)).toBeNull();
  });

  it("rejects values outside the custom union", () => {
    expect(validateAll(pinSchema, true)).toBe("Invalid type: expected pin");
  });

  it("validates the schema type for non-union UI widgets", () => {
    expect(
      validateAll(
        { type: "number", "x-ui-type": "calibration_offset" },
        "not-a-number",
      ),
    ).toBe("Invalid type: expected calibration offset");
    expect(
      validateAll({ type: "integer", "x-ui-type": "motor_direction" }, 1.5),
    ).toBe("Invalid type: expected motor direction");
  });

  it("accepts null declared through a JSON Schema type array", () => {
    expect(validateAll({ type: ["string", "null"] }, null)).toBeNull();
  });
});
