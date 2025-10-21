import { renameKeys } from "rename-obj-map";
import type { JSONSchema, TypeOption } from "@/ui/JsonSchema/interface";
import { pick } from "@/util/obj";
import {
  isNil,
  isEmptyArray,
  isUndefined,
  isString,
  isPlainObject,
  isEmpty,
  isNumber,
  isEmptyString,
} from "@/util/guards";
import { startCase, trimSuffix } from "@/util/str";
import {
  componentsWithDefaults,
  renameMap,
  simpleTypes,
} from "@/ui/JsonSchema/config";

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
  parentSchema?: JSONSchema | null,
  defs?: Record<string, JSONSchema> | undefined,
): number => {
  if (isEmptyArray(effectiveAnyOf)) {
    return 0;
  }

  if (data === null) {
    return effectiveAnyOf.findIndex((item) => item.type === "null");
  }

  if (
    parentSchema?.discriminator &&
    parentSchema.discriminator.propertyName &&
    Object.prototype.hasOwnProperty.call(
      data,
      parentSchema.discriminator.propertyName,
    )
  ) {
    const discVal = data[parentSchema.discriminator.propertyName];
    const mapping = parentSchema.discriminator.mapping;

    const mappedRef = mapping && mapping[discVal];

    if (mappedRef) {
      const rawOptions =
        parentSchema.anyOf ||
        parentSchema.oneOf ||
        parentSchema.items?.anyOf ||
        parentSchema.items?.oneOf ||
        [];

      if (Array.isArray(rawOptions) && rawOptions.length > 0) {
        const exactIdx = rawOptions.findIndex((opt) => opt.$ref === mappedRef);
        if (exactIdx >= 0) {
          return exactIdx;
        }

        const mappedName = mappedRef.split("/").pop();
        if (mappedName) {
          const idxByName = rawOptions.findIndex((opt) => {
            if (opt.$ref) {
              return opt.$ref.split("/").pop() === mappedName;
            }
            const resolved = resolveRef(opt, defs);
            return (
              !!resolved &&
              (resolved.title === mappedName ||
                (resolved as any).$id === mappedName)
            );
          });
          if (idxByName >= 0) {
            return idxByName;
          }
        }
      }
    }
  }

  let bestIndex = 0;
  let bestScore = -1;

  effectiveAnyOf.forEach((schema, index) => {
    if (schema.properties) {
      for (const prop of Object.keys(schema.properties)) {
        const propSchema = (schema.properties as any)[prop];
        if (
          propSchema &&
          !isUndefined(propSchema.const) &&
          Object.prototype.hasOwnProperty.call(data, prop) &&
          (data as any)[prop] === propSchema.const
        ) {
          bestIndex = index;
          bestScore = Number.POSITIVE_INFINITY;
          return;
        }
      }
    }

    let score = 0;
    if (schema.properties) {
      Object.keys(schema.properties).forEach((prop) => {
        if (Object.prototype.hasOwnProperty.call(data, prop)) {
          score++;
        }
      });
    }

    if (schema.type === "integer" && Number.isInteger(data)) {
      score++;
    } else if (schema.type === "number" && isNumber(data)) {
      score++;
    } else if (schema.type === "string" && isString(data)) {
      score++;
    }

    if (bestScore !== Number.POSITIVE_INFINITY && score > bestScore) {
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
  if (!schema || !target) {
    return;
  }

  if (schema.type === "object" && schema.properties) {
    for (const [key, propSchema] of Object.entries(schema.properties)) {
      if (!isUndefined(propSchema?.const)) {
        target[key] = propSchema.const;
      } else if (
        !isUndefined((propSchema as any).default) &&
        (propSchema.shared ? isUndefined(target[key]) : true)
        // !isNull((propSchema as any).default)
      ) {
        target[key] = (propSchema as any).default;
      } else if (isPlainObject(target) && !target.hasOwnProperty(key)) {
        target[key] = null;
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
  if (!resolvedSchema?.type) {
    return;
  }

  const enumOptions = mapEnumOptions(resolvedSchema);

  const compSpec =
    componentsWithDefaults[
      simpleTypes[resolvedSchema.type] && enumOptions
        ? "select"
        : (resolvedSchema?.type as keyof typeof componentsWithDefaults)
    ];

  if (!compSpec) {
    return;
  }

  const extraProps = renameKeys(
    renameMap,
    pick(
      ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "const"],
      resolvedSchema,
    ),
  );

  const overridenProps =
    simpleTypes[resolvedSchema.type] &&
    enumOptions &&
    !extraProps.options &&
    !resolvedSchema?.props?.options
      ? { options: enumOptions }
      : {};

  const comp = compSpec.comp;

  return {
    comp,
    props: {
      ...compSpec.props,
      ...extraProps,
      readonly: !!extraProps.readonly,
      ...overridenProps,
      ...resolvedSchema?.props,
    },
  };
};

export const resolveNewListItem = (
  resolvedSchema: JSONSchema | null,
  selectedOptionIdx: number,
  defs: Record<string, JSONSchema> | undefined,
) => {
  if (isPlainObject(resolvedSchema?.items) && resolvedSchema.items.anyOf) {
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

export const evaluateCondition = (
  model: any,
  condition: { field: string; operator: string; value: any },
): boolean => {
  let expected = condition.value;

  if (typeof expected === "string" && expected.startsWith("$")) {
    const refField = expected.substring(1);
    expected = model ? model[refField] : undefined;
  }
  const actual = model ? model[condition.field] : undefined;

  switch (condition.operator) {
    case "gt":
      return actual > expected;
    case "ge":
      return actual >= expected;
    case "lt":
      return actual < expected;
    case "le":
      return actual <= expected;
    case "eq":
      return actual === expected;
    case "not_eq":
      return actual !== expected;
    case "in":
      return Array.isArray(expected) ? expected.includes(actual) : false;
    case "not_in":
      return Array.isArray(expected) ? !expected.includes(actual) : false;
    default:
      console.warn(`Unsupported operator ${condition.operator}`);
      return true;
  }
};

export const resolveRefRecursive = <Schema extends JSONSchema | TypeOption>(
  schema: Schema,
  defs: Record<string, JSONSchema> | undefined,
) => {
  if (!schema || !isPlainObject(schema)) {
    return schema;
  }

  if (schema.$ref && defs) {
    const refMatch = schema.$ref.match(/^#\/\$defs\/(.+)$/);
    if (refMatch) {
      const defKey = refMatch[1];
      const resolved = defs[defKey];
      if (resolved) {
        schema = { ...resolved, ...schema };
        delete (schema as any).$ref;
      }
    }
  }

  const nestedObjectsKeys = [
    "properties",
    "patternProperties",
    "dependentSchemas",
  ];
  const objectTypes = [
    "not",
    "if",
    "then",
    "else",
    "contains",
    "propertyNames",
    "additionalProperties",
  ] as const;

  const arrTypes = [
    "anyOf",
    "oneOf",
    "allOf",
    "else",
    "contains",
    "propertyNames",
    "additionalProperties",
  ];

  const mixedTypes = ["items"];

  nestedObjectsKeys.forEach((jkey) => {
    const props = (schema as Schema)[jkey as keyof typeof schema] as JSONSchema;
    if (props && isPlainObject(props)) {
      Object.keys(props).forEach((key) => {
        props[key as keyof typeof props] = resolveRefRecursive(
          props[key as keyof typeof props],
          defs,
        );
      });
    }
  });

  arrTypes.forEach((arrKey) => {
    const val = (schema as Schema)[arrKey as keyof typeof schema];
    if (Array.isArray(val)) {
      const mapped = val.map(
        (subSchema) => resolveRefRecursive(subSchema, defs) as JSONSchema,
      );
      (schema as any)[arrKey] = mapped;
    }
  });

  mixedTypes.forEach((arrKey) => {
    const val = (schema as Schema)[arrKey as keyof typeof schema] as
      | JSONSchema
      | JSONSchema[];
    if (!val) {
      return;
    }

    if (Array.isArray(val)) {
      const mapped = val.map(
        (subSchema) => resolveRefRecursive(subSchema, defs) as JSONSchema,
      );
      (schema as any)[arrKey] = mapped;
    } else {
      (schema as any)[arrKey] = resolveRefRecursive(val, defs);
    }
  });

  objectTypes.forEach((key) => {
    const castedKey = key as
      | "not"
      | "if"
      | "then"
      | "else"
      | "contains"
      | "propertyNames"
      | "additionalProperties";

    if (
      (schema as JSONSchema)[castedKey] &&
      isPlainObject((schema as JSONSchema)[castedKey])
    ) {
      (schema as JSONSchema)[castedKey] = resolveRefRecursive(
        (schema as JSONSchema)[castedKey] as JSONSchema,
        defs,
      );
    }
  });

  return schema;
};

export const validateSimpleType = (
  rawSchema: JSONSchema | null,
  effectiveSchema: JSONSchema,
  model: any,
) => {
  let errorMsg: string = "";

  const isNotRequired = (
    rawSchema?.anyOf ||
    rawSchema?.oneOf ||
    rawSchema?.items?.oneOf ||
    rawSchema?.items?.anyOf ||
    []
  ).find((item) => item.type === "null");

  const isModelNull = model === null;
  const isModelValidNull = isNotRequired && isModelNull;

  if (effectiveSchema.type && !isModelValidNull) {
    let validType = true;
    switch (effectiveSchema.type) {
      case "string":
        validType = isString(model) && !isEmptyString(model.trim());
        break;
      case "number":
      case "integer":
        validType = typeof model === "number";
        if (effectiveSchema.type === "integer" && !Number.isInteger(model)) {
          validType = false;
        }
        break;
      case "boolean":
        validType = typeof model === "boolean";
        break;
      case "null":
        validType = model === null;
        break;

      case "string_or_number":
      case "pin":
        validType = isString(model)
          ? !isEmptyString(model.trim())
          : isNumber(model);
        break;
      case "hex":
        if (typeof model === "number") {
          validType = true;
        } else if (isString(model)) {
          validType = /^0x[0-9a-fA-F]+$/.test(model);
          if (!validType) {
            errorMsg = "Invalid hex number!";
          }
        } else {
          validType = false;
        }
        break;
      default:
        validType = true;
    }

    if (!isEmptyString(errorMsg)) {
      return errorMsg;
    }
    if (!validType) {
      errorMsg =
        isNil(model) || (isString(model) && isEmptyString(model.trim()))
          ? "Required"
          : `Invalid type: expected ${(rawSchema?.type || effectiveSchema.type).replace("_", " ")}`;

      return errorMsg;
    }
  }

  if (isNumber(model)) {
    if (
      effectiveSchema.minimum !== undefined &&
      model < effectiveSchema.minimum
    ) {
      errorMsg += ` Must be >= ${effectiveSchema.minimum}.`;
    }
    if (
      effectiveSchema.maximum !== undefined &&
      model > effectiveSchema.maximum
    ) {
      errorMsg += ` Must be <= ${effectiveSchema.maximum}.`;
    }
    if (
      effectiveSchema.exclusiveMinimum !== undefined &&
      model <= effectiveSchema.exclusiveMinimum
    ) {
      errorMsg += ` Must be > ${effectiveSchema.exclusiveMinimum}.`;
    }
    if (
      effectiveSchema.exclusiveMaximum !== undefined &&
      model >= effectiveSchema.exclusiveMaximum
    ) {
      errorMsg += ` Must be < ${effectiveSchema.exclusiveMaximum}.`;
    }
  }

  if (isString(model) && effectiveSchema.pattern) {
    const reg = new RegExp(effectiveSchema.pattern);
    if (!reg.test(model)) {
      errorMsg += ` Must match pattern "${effectiveSchema.pattern}".`;
    }
  }

  if (Array.isArray(effectiveSchema.enum) && effectiveSchema.enum.length > 0) {
    if (!effectiveSchema.enum.includes(model)) {
      errorMsg += ` Value must be one of: ${effectiveSchema.enum.join(", ")}.`;
    }
  }

  return errorMsg.trim().length > 0 ? errorMsg : null;
};

export const validateAll = (
  rawSchema: JSONSchema | null,
  model: any,
  defs?: Record<string, JSONSchema> | undefined,
): any => {
  if (!rawSchema) return null;

  let effectiveSchema: JSONSchema = rawSchema;

  if (
    rawSchema.anyOf ||
    rawSchema.oneOf ||
    rawSchema.items?.anyOf ||
    rawSchema.items?.oneOf
  ) {
    const options =
      rawSchema.anyOf ||
      rawSchema.oneOf ||
      rawSchema.items?.anyOf ||
      rawSchema.items?.oneOf;

    if (options) {
      const candidateIndex = detectCandidateIndex(
        model,
        options as JSONSchema[],
        rawSchema,
        defs,
      );

      effectiveSchema = (options[candidateIndex] || rawSchema) as JSONSchema;
    }
  }

  if (!effectiveSchema) {
    return null;
  }

  let errors: Record<string, any> = {};

  if (Array.isArray(rawSchema.cross_field_validation)) {
    rawSchema.cross_field_validation.forEach((rule) => {
      const allConditionsPass = rule.conditions.every((cond) =>
        evaluateCondition(model, cond),
      );
      if (allConditionsPass) {
        errors[rule.then.field] = rule.then.rule.message;
      }
    });
  }

  if (
    (effectiveSchema.type === "object" || effectiveSchema.properties) &&
    effectiveSchema.properties
  ) {
    if (Array.isArray(effectiveSchema.required)) {
      effectiveSchema.required.forEach((requiredKey) => {
        if (model === undefined || model === null || !(requiredKey in model)) {
          errors[requiredKey] = "This field is required.";
        }
      });
    }

    Object.entries(effectiveSchema.properties).forEach(([key, propSchema]) => {
      const childValue = model ? model[key] : undefined;
      const childErrors = validateAll(propSchema, childValue, defs);
      if (
        childErrors &&
        (isString(childErrors) || Object.keys(childErrors).length > 0)
      ) {
        errors[key] = childErrors;
      }
    });
  } else if (
    (effectiveSchema.type === "array" || effectiveSchema.items) &&
    effectiveSchema.items
  ) {
    if (!Array.isArray(model)) {
      return "Expected an array.";
    } else {
      const arrErrors = model.map((item: any) =>
        validateAll(effectiveSchema.items!, item, defs),
      );

      if (
        arrErrors.some(
          (itemErr) =>
            itemErr && (isString(itemErr) || Object.keys(itemErr).length > 0),
        )
      ) {
        return arrErrors;
      }
    }
  } else if (isEmpty(errors)) {
    return validateSimpleType(rawSchema, effectiveSchema, model);
  }

  return isEmpty(errors) ? null : errors;
};
