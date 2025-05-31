import { isPlainObject } from "@/util/guards";

/**
 * A utility function to validate objects against a set of predicate functions.
 * Can either produce a curried predicate or immediately validate an object.
 *
 * @example
 * // Validate synchronously
 * where({ width: isNumber, height: isNumber }, { width: 100, height: 200 }); // true
 *
 * // Curried check
 * const validate = where({ width: isNumber, height: isNumber });
 * validate({ width: 100, height: undefined }); // false
 *
 * @typeParam Obj - The type of the input object to be validated.
 * @typeParam Spec - A specification object defining predicates for properties of `Obj`.
 * Properties of `Spec` should be functions that accept `Obj[P]` and return a boolean.
 */
export function where<
  Obj,
  R extends Obj,
  Spec = {
    [P in keyof Obj as P]?: (val: Obj[P]) => boolean;
  },
>(spec: Spec): <Obj, R extends Obj>(obj: Obj) => obj is R;
/**
 * A utility function to validate objects against a set of predicate functions.
 * Can either produce a curried predicate or immediately validate an object.
 *
 * @param spec - An object where each key is a property to validate,
 *               and each value is a predicate function used to validate its corresponding property.
 * @param obj - The object to be validated.
 * @returns Whether the object matches the validation specification.
 *
 * @example
 * // Validate synchronously
 * where({ width: isNumber, height: isNumber }, { width: 100, height: 200 }); // true
 */
export function where<
  Obj,
  R extends Obj,
  Spec = {
    [P in keyof Obj as P]?: (val: Obj[P]) => boolean;
  },
>(spec: Spec, obj: Obj): obj is R;
/**
 * Implementation of the `where` function that supports both overload variants:
 * - Returns a curried function if only `spec` is provided.
 * - Immediately validates `obj` if both `spec` and `obj` are provided.
 *
 * @param spec - Validation specification object.
 *               Each property is a predicate that validates the corresponding property in the input object.
 * @param obj - The object to validate (if provided).
 * @returns A boolean indicating validity, or a type guard function.
 */
export function where<Obj>(
  spec: { [P in keyof Obj as P]?: (val: Obj[P]) => boolean },
  obj?: Obj,
) {
  return arguments.length === 1
    ? <Obj>(obj: Obj) =>
        !isPlainObject(obj)
          ? false
          : Object.keys(spec).every((k) => {
              const fn = spec[k as keyof typeof spec];
              return !fn || fn(obj[k]);
            })
    : !isPlainObject(obj)
      ? false
      : Object.keys(spec).every((k) => {
          const fn = spec[k as keyof typeof spec];
          return !fn || fn(obj[k]);
        });
}

export function isShallowEq<A, B extends A>(valueA: A): (valueB: B) => boolean;
export function isShallowEq<A, B extends A>(valueA: A, valueB: B): boolean;
export function isShallowEq<A, B extends A>(valueA: A, valueB?: B) {
  return arguments.length === 1
    ? (valueB: B) => valueA === valueB
    : valueA === valueB!;
}

export function allPass(
  fns: ((...args: any) => boolean)[],
): <T>(value: T) => boolean;

export function allPass<T>(
  fns: ((...args: any) => boolean)[],
  value: T,
): boolean;
export function allPass<T>(fns: ((...args: any) => boolean)[], value?: T) {
  return arguments.length === 1
    ? <T>(value: T) => fns.every((fn) => fn(value))
    : fns.every((fn) => fn(value));
}
