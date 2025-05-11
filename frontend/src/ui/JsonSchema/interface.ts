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

export interface JSONSchemaBase {
  title: string;
  type?: FieldType;
  description?: string;
  enum?: (number | string)[];
  anyOf?: JSONSchema[];
  oneOf?: JSONSchema[];
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
  props?: Record<string, any>;
  ge?: number;
  le?: number;
  discriminator?: any;
  const?: string;
}

export interface JSONSchema extends JSONSchemaBase {
  properties?: Record<string, JSONSchema>;
  $defs?: Record<string, JSONSchema>;
}
