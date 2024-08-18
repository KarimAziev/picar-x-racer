export const isString = (v: any): v is string => typeof v === "string";
export const isFunction = (v: any): v is Function => typeof v === "function";
export const isNumber = (v: any): v is number => typeof v === "number";

/**
 * Checks if a given value is a plain object.
 *
 * A plain object is an object that is created by the Object constructor or
 * one with a prototype of null.
 *
 * @param value - The value to check.
 * @returns True if the value is a plain object, false otherwise.
 */
export const isPlainObject = (value: any): value is Record<string, any> => {
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

export const isError = (error: any): error is Error => error instanceof Error;

export const isEmptyString = (value: any) => isString(value) && !value.length;
export const isEmptyArray = (value: any) => isArray(value) && !value.length;

export const isEmpty = (value: any) =>
  (isArray(value) || isString(value)) && !value.length;
