export const isString = (v: unknown): v is string => typeof v === "string";
export const isFunction = (v: unknown): v is Function =>
  typeof v === "function";
export const isNumber = (v: unknown): v is number => typeof v === "number";

/**
 * Checks if a given value is a plain object.
 *
 * A plain object is an object that is created by the Object constructor or
 * one with a prototype of null.
 *
 * @param value - The value to check.
 * @returns True if the value is a plain object, false otherwise.
 */
export const isPlainObject = (value: unknown): value is Record<string, any> => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const proto = Object.getPrototypeOf(value);

  // Check for Object.create(null)
  if (proto === null) {
    return true;
  }

  // Check if the prototype object is exactly the prototype object of Object
  return proto === Object.prototype;
};

export const isArray = Array.isArray;

export const isError = (error: unknown): error is Error =>
  error instanceof Error;

export const isEmptyString = (value: unknown) =>
  isString(value) && !value.length;
export const isEmptyArray = (value: unknown) => isArray(value) && !value.length;

export const isEmpty = (value: unknown) =>
  isArray(value) || isString(value)
    ? value.length === 0
    : isPlainObject(value)
      ? Object.keys(value).length === 0
      : false;

export const isBigint = (v: unknown): v is bigint => typeof v === "bigint";
export const isBoolean = (v: unknown) => typeof v === "boolean";
export const isSymbol = (v: unknown): v is symbol => typeof v === "symbol";
export const isNull = (v: unknown): v is null => v === null;
export const isUndefined = (v: unknown): v is undefined => v === undefined;

export const isInput = (v: unknown): v is HTMLInputElement =>
  v instanceof HTMLInputElement;
export const isButton = (v: unknown): v is HTMLButtonElement =>
  v instanceof HTMLButtonElement;

export const isNil = (v: unknown): v is null | undefined =>
  isNull(v) || isUndefined(v);

export const isImage = (v: unknown): v is HTMLImageElement =>
  v instanceof HTMLImageElement;
