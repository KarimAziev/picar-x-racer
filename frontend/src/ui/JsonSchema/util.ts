import { renameKeys } from "rename-obj-map";
import type { JSONSchema, TypeOption } from "@/ui/JsonSchema/interface";
import { pick } from "@/util/obj";
import {
  isNil,
  isEmptyArray,
  isUndefined,
  isString,
  isPlainObject,
} from "@/util/guards";
import { startCase, trimSuffix } from "@/util/str";
import { componentsWithDefaults, renameMap } from "@/ui/JsonSchema/config";

export const setNestedValue = <Obj extends Record<string, any> | null>(
  obj: Obj,
  keys: (string | number)[],
  value: any,
): void => {
  if (!obj) {
    return;
  }
  keys.reduce((acc, key, index) => {
    if (index === keys.length - 1) {
      acc[key] = value;
    } else {
      if (isNil(acc[key])) {
        acc[key] = {};
      }
      return acc[key];
    }
  }, obj);
};

export const getNestedValue = <Obj extends Record<string | number, any> | null>(
  obj: Obj,
  keys: (string | number)[],
) => keys.reduce((acc, key) => (acc ? acc[key] : undefined), obj);

export const isObjectSchemaPred = (resolvedSchema: JSONSchema | null) =>
  resolvedSchema?.type === "object" && !!resolvedSchema.properties;

export const isArraySchemaPred = (resolvedSchema: JSONSchema | null) =>
  resolvedSchema?.type === "array" && resolvedSchema.items;

export const isAnyOfPred = (resolvedSchema: JSONSchema | null) =>
  !!(resolvedSchema?.anyOf && Array.isArray(resolvedSchema?.anyOf)) ||
  !!(resolvedSchema?.oneOf && Array.isArray(resolvedSchema?.oneOf));

export const mapEffectiveAnyOf = (
  resolvedSchema: JSONSchema | null,
  defs: Record<string, JSONSchema> | undefined,
) =>
  (
    resolvedSchema?.items?.anyOf ||
    resolvedSchema?.items?.oneOf ||
    resolvedSchema?.anyOf ||
    resolvedSchema?.oneOf ||
    []
  ).map((opt) => resolveRef(opt, defs) || opt);

export const mapAnyOfOptions = (effectiveAnyOf: JSONSchema[]) =>
  effectiveAnyOf.map((sch, i) => {
    let label = "";
    if (sch.title) {
      label = sch.title;
    } else if (sch.$ref) {
      label = sch.$ref.split("/").pop() || `Option ${i + 1}`;
    } else if (sch.type) {
      label = sch.type;
    } else {
      label = `Option ${i + 1}`;
    }
    return { value: i, label: startCase(label) };
  });

export const mapEnumOptions = (resolvedSchema: JSONSchema | null) =>
  Array.isArray(resolvedSchema?.props?.options)
    ? resolvedSchema.props.options
    : Array.isArray(resolvedSchema?.enum)
      ? resolvedSchema?.enum.map((value) => ({
          value,
          label: isString(value) ? startCase(value) : `${value}`,
        }))
      : undefined;

export const detectCandidateIndex = (
  data: Record<string | number, any> | null,
  effectiveAnyOf: JSONSchema[],
): number => {
  if (!data || isEmptyArray(effectiveAnyOf)) {
    return 0;
  }
  let bestIndex = 0;
  let bestScore = -1;

  effectiveAnyOf.forEach((schema, index) => {
    let score = 0;
    if (schema.properties) {
      Object.keys(schema.properties).forEach((prop) => {
        if (data.hasOwnProperty(prop)) {
          score++;
        }
      });
    }
    if (score > bestScore) {
      bestScore = score;
      bestIndex = index;
    }
  });
  return bestIndex;
};

export const fillDefaults = (
  target: Record<string, any>,
  schema: JSONSchema,
): void => {
  if (!schema || !target) return;
  if (schema.type === "object" && schema.properties) {
    for (const [key, propSchema] of Object.entries(schema.properties)) {
      if (!isUndefined(propSchema?.const)) {
        target[key] = propSchema.const;
      } else if (
        isUndefined(target[key]) &&
        !isUndefined((propSchema as any).default)
      ) {
        target[key] = (propSchema as any).default;
      }
      if (
        propSchema &&
        typeof target[key] === "object" &&
        propSchema.type === "object"
      ) {
        fillDefaults(target[key], propSchema);
      }
    }

    for (const key in target) {
      if (!schema.properties[key]) {
        delete target[key];
      }
    }
  }
};

export const makeDefaults = (
  schema: JSONSchema,
  extraObj?: Record<string, any>,
) => {
  if (!schema || !schema.properties) return;
  return Object.entries(schema.properties).reduce(
    (acc, [key, propSchema]) => {
      const obj = extraObj ? extraObj[key] : undefined;
      const defaultVal = propSchema.default;

      const value = !isUndefined(propSchema?.const)
        ? propSchema.const
        : obj &&
            !Array.isArray(obj) &&
            !isPlainObject(obj) &&
            typeof obj === typeof propSchema.default
          ? obj
          : !isUndefined(defaultVal)
            ? defaultVal
            : propSchema?.type === "object"
              ? makeDefaults(propSchema, obj)
              : undefined;
      acc[key] = value;
      return acc;
    },
    {} as Record<string, any>,
  );
};

export const resolveRef = (
  schema: JSONSchema | TypeOption,
  defs: Record<string, JSONSchema> | undefined,
) => {
  if (schema?.$ref && defs) {
    const refMatch = schema.$ref.match(/^#\/\$defs\/(.+)$/);
    if (refMatch) {
      const defKey = refMatch[1];
      return defs[defKey] || schema;
    }
  }
};

export const getSelectedSchema = (
  options: JSONSchema[],
  selectedOption: number,
  defs: Record<string, JSONSchema> | undefined,
) => {
  if (!options || isEmptyArray(options)) {
    return null;
  }
  if (options.length === 1) {
    return options[0];
  }

  const index = selectedOption ?? 0;
  return resolveRef(options[index], defs) || options[index];
};

export const getTooltipHelp = (resolvedSchema: JSONSchema | null) => {
  if (!resolvedSchema) {
    return;
  }
  const examples = resolvedSchema.examples?.map((it) => `${it}`);
  const examplesStr = examples && examples.length > 0 && examples.join(", ");
  const description = resolvedSchema.description || resolvedSchema.tooltipHelp;
  if (description) {
    return [trimSuffix(description, ".").trim(), examplesStr]
      .filter(Boolean)
      .join(", e.g. ");
  }

  return examplesStr ? `Examples: ${examplesStr}` : undefined;
};

export const getComponentWithProps = (resolvedSchema: JSONSchema | null) => {
  const compSpec =
    componentsWithDefaults[
      resolvedSchema?.type as keyof typeof componentsWithDefaults
    ];

  if (!resolvedSchema?.type || !compSpec) {
    return;
  }

  const extraProps = renameKeys(
    renameMap,
    pick(
      ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "const"],
      resolvedSchema,
    ),
  );

  const comp = compSpec.comp;

  return {
    comp,
    props: {
      ...compSpec.props,
      ...extraProps,
      readonly: !!extraProps.readonly,
      ...resolvedSchema?.props,
    },
  };
};

export const resolveNewListItem = (
  resolvedSchema: JSONSchema | null,
  selectedOptionIdx: number,
  defs: Record<string, JSONSchema> | undefined,
) => {
  if (resolvedSchema?.items && resolvedSchema.items.anyOf) {
    const selectedBranch =
      resolvedSchema.items.anyOf[selectedOptionIdx] &&
      resolveRef(resolvedSchema.items.anyOf[selectedOptionIdx], defs);

    if (selectedBranch?.type === "object") {
      return makeDefaults(selectedBranch);
    }
  } else if (resolvedSchema?.items && resolvedSchema.items.type === "object") {
    return makeDefaults(resolvedSchema.items);
  } else if (resolvedSchema?.items && resolvedSchema.items.enum) {
    return resolvedSchema.items.enum[0];
  } else if (resolvedSchema?.items?.$ref) {
    const schema = resolveRef(resolvedSchema?.items, defs);
    if (schema) {
      return makeDefaults(schema);
    } else {
      return {};
    }
  } else {
    return null;
  }
};
