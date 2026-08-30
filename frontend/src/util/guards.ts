/**
 * A type guard function that narrows a value of type `T` to the subtype `S`.
 */
export type Guard<T, S extends T> = (value: T) => value is S;

/**
 * Cast a boolean predicate into a typed `Guard`.
 *
 * Useful when you *know* the predicate performs a narrowing check, but TypeScript
 * can't infer it automatically.
 *
 * @param fn - Predicate function.
 * @returns The same function typed as a type guard.
 */
export function asGuard<T, S extends T>(
  fn: (value: T) => boolean,
): Guard<T, S> {
  return fn as Guard<T, S>;
}

/**
 * Negate a type guard while preserving type information.
 *
 * Returns a new type guard that narrows `T` to `Exclude<T, S>` when the original
 * guard fails.
 * @param g - Guard to negate.
 * @returns A guard that passes when `g` fails.
 */
export function notGuard<T, S extends T>(
  g: Guard<T, S>,
): Guard<T, Exclude<T, S>> {
  return ((value: T) => !g(value)) as Guard<T, Exclude<T, S>>;
}

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

export const isEmptyString = (value: unknown): value is "" => value === "";

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

export const isObjectLike = (v: unknown): v is object =>
  typeof v === "object" && !isNull(v);

export const isUndefined = (v: unknown): v is undefined => v === undefined;

export const isInput = (v: unknown): v is HTMLInputElement =>
  v instanceof HTMLInputElement;
export const isButton = (v: unknown): v is HTMLButtonElement =>
  v instanceof HTMLButtonElement;

export const isNil = (v: unknown): v is null | undefined =>
  isNull(v) || isUndefined(v);

export const isImage = (v: unknown): v is HTMLImageElement =>
  v instanceof HTMLImageElement;

export const isEmptyArray = (value: unknown): value is [] =>
  isArray(value) && !value.length;

export const isNonEmptyArray = (value: unknown): value is unknown[] =>
  isArray(value) && value.length > 0;

/**
 * Combine multiple predicates/guards into a single predicate that passes when
 * any predicate passes (`OR`).
 *
 * Supports both:
 * - variadic arguments: `anyPass(p1, p2, p3)`
 * - a single array: `anyPass([p1, p2, p3])`
 *
 * When provided with type guards, the resulting function is also a type guard
 * that narrows to the union of the guarded types.
 *
 * @example
 * ```ts
 * const isStringOrNumber = anyPass(isString, isNumber)
 * const v = Math.random() > 0.5 ? {b: "x"} : 1
 *   if (isStringOrNumber(v)) {
 *     const newV = v; // infers as const newV: 1
 *   }
 * ```
 */
export function anyPass<T, S extends readonly any[]>(
  ...predicates: { [K in keyof S]: (value: T) => value is S[K] }
): (value: T) => value is S[number];
export function anyPass<T, S extends T>(
  predicates: ReadonlyArray<Guard<T, S>>,
): Guard<T, S>;
export function anyPass<T>(
  predicates: ReadonlyArray<(value: T) => boolean>,
): (value: T) => boolean;
export function anyPass<T>(
  ...predicates: Array<(value: T) => boolean>
): (value: T) => boolean;

export function anyPass<T>(
  first: ReadonlyArray<(value: T) => boolean> | ((value: T) => boolean),
  ...rest: Array<(value: T) => boolean>
) {
  const preds = Array.isArray(first) ? first : [first, ...rest];
  return (value: T) => preds.some((p) => p(value));
}
/**
 * Combine multiple predicates/guards into a single predicate that passes when
 * **all** predicates pass (`AND`).
 *
 * Supports both:
 * - variadic arguments: `allPass(p1, p2, p3)`
 * - a single array: `allPass([p1, p2, p3])`
 *
 * When provided with type guards, the resulting function narrows to the
 * intersection-like union `S[number]` (commonly used to build refined guards).
 */
export function allPass<T, S extends readonly any[]>(
  ...predicates: { [K in keyof S]: (value: T) => value is S[K] }
): (value: T) => value is S[number];

export function allPass<T, S extends T>(
  predicates: ReadonlyArray<Guard<T, S>>,
): Guard<T, S>;
export function allPass<T>(
  predicates: ReadonlyArray<(value: T) => boolean>,
): (value: T) => boolean;
export function allPass<T>(
  ...predicates: Array<(value: T) => boolean>
): (value: T) => boolean;

export function allPass<T>(
  first: ReadonlyArray<(value: T) => boolean> | ((value: T) => boolean),
  ...rest: Array<(value: T) => boolean>
) {
  const preds = Array.isArray(first) ? first : [first, ...rest];
  return (value: T) => preds.every((p) => p(value));
}

/**
 * Logical negation for a predicate function.
 *
 * - If given a type guard, the returned function is a boolean predicate
 *   (not a type guard).
 * - If given a regular boolean function, the returned function preserves the
 *   same parameter list and returns the negated boolean.
 *
 * @param fn - Predicate to negate.
 * @returns A function that returns `!fn(...)`.
 */
export function not<T, S extends T>(fn: Guard<T, S>): (value: T) => boolean;
export function not<A extends readonly unknown[]>(
  fn: (...args: A) => boolean,
): (...args: A) => boolean;
export function not(fn: (...args: any[]) => boolean) {
  return (...args: any[]) => !fn(...args);
}

export const isNonEmptyString = asGuard<unknown, Exclude<string, "">>(
  allPass(isString, notGuard(isEmptyString)),
);
