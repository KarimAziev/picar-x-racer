export type MethodsWithoutParams<T> = {
  [K in keyof T as T[K] extends (...args: infer P) => any
    ? P extends []
      ? K
      : never
    : never]: T[K] extends (...args: infer _P) => any ? T[K] : never;
};

export type MethodsWithOneStringParam<T> = {
  [K in keyof T as T[K] extends (...args: infer P) => any
    ? P extends [string]
      ? K
      : never
    : never]: T[K] extends (...args: infer _P) => any ? T[K] : never;
};

/**
 * Cast type A to type B if A is assignable to B, otherwise, default to B.
 * @param A - The type to cast.
 * @param B - The target type to cast to.
 * @returns Either A if it is assignable to B, or B.
 */
export type Cast<A, B> = A extends B ? A : B;

/**
 * A union of types that are considered "narrowable" which means their type is not widened in certain contexts.
 */
export type Narrowable = string | number | bigint | boolean;

/**
 * Recursively narrow the types in object `A`, preventing them from being widened.
 * If the value is of a `Narrowable` type, it remains as is, otherwise it is replaced with `never`.
 * For objects, each property is recursively narrowed.
 * @param A - The type to recursively narrow.
 * @returns The recursively narrowed type.
 */
export type Narrow<A> = Cast<
  A,
  [] | (A extends Narrowable ? A : never) | { [K in keyof A]: Narrow<A[K]> }
>;

// return first element from Array
export type First<T> = T extends any[] ? T[0] : never;

export type ExcludePrefix<
  Prefix extends string,
  Str extends string,
> = Str extends `${Prefix}${string}` ? never : Str;

export type ExcludePropertiesWithPrefix<
  Prefix extends string,
  T extends Record<string, any>,
> = {
  [K in keyof T as K extends `${Prefix}${string}` ? never : K]: T[K];
};

export declare type Nullable<T = void> = T | null | undefined;

export type RecoursiveRequired<T> = {
  [K in keyof Required<T> as K]: Required<T>[K] extends object
    ? RecoursiveRequired<Required<T>[K]>
    : T[K];
};

/**
 * @example
 * ```ts
 * export type Result = FlattenObjectKeys<{
 *   propA: "3";
 *   propB: {
 *     nestedProp: {
 *       arr: [{ a: 1 }, { b: 3 }];
 *     };
 *   };
 * }>;
 *
 * // -> "propA" | "propB.nestedProp.arr"
 * ```
 */
export type FlattenObjectKeys<
  T extends Record<string, any>,
  Key = keyof T,
> = Key extends string
  ? Required<T>[Key] extends any[]
    ? `${Key}`
    : Required<T>[Key] extends Record<string, any>
      ? `${Key}.${FlattenObjectKeys<Required<T>[Key]>}`
      : `${Key}`
  : never;

/**
 * @example
 * ```ts
 * export type Result = NonFlattenObjectKeys<{
 *   propA: "3";
 *   propB: {
 *     nestedProp: {
 *       arr: [{ a: 1 }, { b: 3 }];
 *     };
 *   };
 * }>;
 * // -> "propA"
 * ```
 */
export type NonFlattenObjectKeys<
  T extends Record<string, any>,
  Key = keyof T,
> = Key extends string
  ? Required<T>[Key] extends Record<string, any>
    ? never
    : `${Key}`
  : never;

/**
 * @example
 * ```ts
 * FlattenObject<{
 *   propA: "3";
 *   propB: {
 *     nestedProp: {
 *       arr: [{ a: 1 }, { b: 3 }];
 *     };
 *   };
 * }>;
 *
 * // -> {
 *     propA: "3";
 *     "propB.nestedProp.arr": [{
 *         a: 1;
 *     }, {
 *         b: 3;
 *     }];
 * }
 * ```
 */

export type FlattenObject<T extends Record<string, any>> = {
  [K in FlattenObjectKeys<T>]: K extends `${infer Key}.${infer Rest}`
    ? Key extends keyof T
      ? Rest extends FlattenObjectKeys<T[Key]>
        ? FlattenObject<T[Key]>[Rest]
        : never
      : never
    : K extends keyof T
      ? T[K]
      : never;
};

/**
 * @example
 * ```ts
 * export type Result = FlattenAllObjectKeys<{
 *   propA: "3";
 *   propB: {
 *     nestedProp: {
 *       arr: [{ a: 1 }, { b: 3 }];
 *     };
 *   };
 * }>;
 *
 * // "propA" | "propB" | "propB.nestedProp" | "propB.nestedProp.arr"
 * ```
 */
export type FlattenAllObjectKeys<T> = {
  [K in keyof Required<T> & string]: Required<T>[K] extends any[]
    ? K
    : Required<T>[K] extends Record<string, any>
      ? K | `${K}.${FlattenAllObjectKeys<Required<T>[K]>}`
      : K;
}[keyof Required<T> & string];

export type Prepend<K extends string | number, P> = P extends any[]
  ? [K, ...P]
  : never;

/**
 * @example
 * ```ts
 * FlattenAllObjectKeysPaths<{
 *   propA: "3";
 *   propB: {
 *     nestedProp: {
 *       arr: [{ a: 1 }, { b: 3 }];
 *     };
 *   };
 * }>; // -> ["propA"] | ["propB"] | ["propB", "nestedProp"] | ["propB", "nestedProp", "arr"]
 * ```
 */

export type FlattenAllObjectKeysPaths<T> = {
  [K in keyof Required<T> & string]: Required<T>[K] extends any[]
    ? [K]
    : Required<T>[K] extends Record<string, any>
      ? [K] | Prepend<K, FlattenAllObjectKeysPaths<Required<T>[K]>>
      : [K];
}[keyof Required<T> & string];

export type FlattenBooleanObjectKeys<
  T extends Record<string, any>,
  Key = keyof T & string, // Force only string-based keys
> = Key extends string
  ? T[Key] extends Record<string, any>
    ? `${Key}.${FlattenBooleanObjectKeys<T[Key]>}`
    : T[Key] extends boolean
      ? `${Key}`
      : never
  : never;

export type ExtractStringPropsKey<Obj extends Record<string, any>> = {
  [Key in keyof Obj]: Obj[Key] extends string ? Key : never;
}[keyof Obj];

/**
 * Utility type to make all properties of a type required (non-optional).
 *
 * @example
 * type Example = { a?: number; b: string };
 * type Result = Defined<Example>;
 * // Result: { a: number; b: string }
 */
export type Defined<T> = {
  [P in keyof T]-?: T[P];
};

export type DeepObjectsToHandlers<Obj, NoNils extends boolean> = {
  [P in keyof Obj]: Obj[P] extends Record<string, any>
    ? DeepObjectsToHandlers<Obj[P], NoNils>
    : NoNils extends true
      ? (value: NonNullable<Obj[P]>) => void
      : (value: Obj[P]) => void;
};

export type MapObjectsDeepTo<Obj, Value> = {
  [P in keyof Obj]: Obj[P] extends Record<string, any>
    ? MapObjectsDeepTo<Obj[P], Value>
    : Value;
};

export type PropertiesOfType<T, U> = {
  [K in keyof T as T[K] extends U ? K : never]: T[K];
};

type Prev = [never, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

type Decrement<D extends number> = Prev[D];

/**
 * @example
 * ```ts
 * // with object
 * FlattenPaths<{
 *   propA: "3";
 *   propB: {
 *     nested_arr: [{ a: 1 }, { b: 3 }];
 *   };
 * }>;
 * // ->
 *   ["propA"] |
 *   ["propB"] |
 *   ["propB", "nested_arr"] |
 *   ["propB", "nested_arr", number] |
 *   ["propB", "nested_arr", number, "a"] |
 *   ["propB", "nested_arr", number, "b"];
 *
 * // with array
 * FlattenPaths<[{ a: 1 }, { b: 3 }]> // -> [number] | [number, "a"] | [number, "b"]
 *
 * FlattenPaths<[{ a: 1, nested: { c: 2} }, { b: 3 }]>
 * // -> [number] | [number, "a"] | [number, "nested"] | [number, "nested", "c"] | [number, "b"]
 * ```
 */

export type FlattenPaths<T, D extends number = 10> = D extends 0
  ? []
  : T extends any[]
    ? FlattenArrayPaths<T, D>
    : T extends object
      ? FlattenObjectPaths<T, D>
      : [];

/**
 * @example
 * ```ts
 * FlattenObjectPaths<{
 *   propA: "3";
 *   propB: {
 *     nested_arr: [{ a: 1 }, { b: 3 }];
 *   };
 * }>;
 * ->
 *   ["propA"] |
 *   ["propB"] |
 *   ["propB", "nested_arr"] |
 *   ["propB", "nested_arr", number] |
 *   ["propB", "nested_arr", number, "a"] |
 *   ["propB", "nested_arr", number, "b"];
 * ```
 */
export type FlattenObjectPaths<T, D extends number> = {
  [K in keyof Required<T> & string]: Required<T>[K] extends any[]
    ? [K] | Prepend<K, FlattenArrayPaths<Required<T>[K], Decrement<D>>>
    : Required<T>[K] extends object
      ? [K] | Prepend<K, FlattenPaths<Required<T>[K], Decrement<D>>>
      : [K];
}[keyof Required<T> & string];

/**
 * @example
 * ```ts
 * // with array
 * FlattenArrayPaths<[{ a: 1 }, { b: 3 }]> // -> [number] | [number, "a"] | [number, "b"]
 *
 * FlattenArrayPaths<[{ a: 1, nested: { c: 2} }, { b: 3 }]>
 * // -> [number] | [number, "a"] | [number, "nested"] | [number, "nested", "c"] | [number, "b"]
 * ```
 */
export type FlattenArrayPaths<T extends any[], D extends number> =
  | [number]
  | Prepend<number, FlattenPaths<T[number], Decrement<D>>>;

/**
 * @example
 * ```ts
 * GetTypeByPath<{ a: 3; b: { c: "val" } }, ["b", "c"]>; // -> "val"
 * ```
 */
export type GetTypeByPath<
  T,
  Path extends Array<any>,
  D extends number = 10,
> = D extends 0
  ? never
  : Path extends [infer Head, ...infer Rest]
    ? Head extends keyof T // object key case
      ? GetTypeByPath<
          T[Head],
          Extract<Rest, Array<string | number>>,
          Decrement<D>
        >
      : Head extends number // array index case
        ? T extends Array<infer U>
          ? GetTypeByPath<
              U,
              Extract<Rest, Array<string | number>>,
              Decrement<D>
            >
          : never
        : never
    : T;
