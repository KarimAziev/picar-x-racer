import { ValueLabelOption } from "@/types/common";

export type FieldType =
  | "integer"
  | "string"
  | "number"
  | "boolean"
  | "object"
  | "hex"
  | "null"
  | "array"
  | "string_or_number";

export type TypeOption = {
  type?: FieldType;
  minimum?: number;
  $ref?: string;
  anyOf?: Options;
};

export type Options = TypeOption[];

export interface Props extends Record<string, any> {
  options?: ValueLabelOption<number | string>[];
  hidden?: boolean;
}

export type Operator =
  | "gt"
  | "lt"
  | "ge"
  | "le"
  | "eq"
  | "not_eq"
  | "in"
  | "not_in";

// simple DSL condition for validation
export interface Condition {
  field: string;
  operator: Operator;
  value: any;
}

export interface ValidationRuleResult {
  message: string;
}

export interface CrossFieldRule {
  conditions: Condition[];
  then: {
    field: string;
    rule: ValidationRuleResult;
  };
}

export interface JSONSchemaBase {
  title?: string;
  type?: FieldType;
  description?: string;
  enum?: (number | string)[];
  anyOf?: JSONSchema[];
  oneOf?: JSONSchema[];
  allOf?: JSONSchema[];
  not?: JSONSchema;
  if?: JSONSchema;
  then?: JSONSchema;
  else?: JSONSchema;
  dependentSchemas?: JSONSchema;
  patternProperties?: JSONSchema;
  additionalProperties?: JSONSchema;
  propertyNames?: JSONSchema;
  contains?: JSONSchema;
  default?: any;
  examples?: (string | number)[];
  items?: JSONSchema;
  $ref?: string;
  required?: string[];
  minimum?: number;
  maximum?: number;
  exclusiveMaximum?: number;
  exclusiveMinimum?: number;
  pattern?: string;
  uniqueItems?: string;
  tooltipHelp?: string;
  props?: Props;
  ge?: number;
  le?: number;
  discriminator?: any;
  const?: string;
  cross_field_validation?: CrossFieldRule[];
}

export interface JSONSchema extends JSONSchemaBase {
  properties?: Record<string, JSONSchema>;
  $defs?: Record<string, JSONSchema>;
}
