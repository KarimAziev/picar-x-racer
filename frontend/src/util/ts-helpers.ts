export type MethodsWithoutParams<T> = {
  [K in keyof T as T[K] extends (...args: infer P) => any
    ? P extends []
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

export type FlattenObjectKeys<
  T extends Record<string, any>,
  Key = keyof T,
> = Key extends string
  ? Required<T>[Key] extends Record<string, any>
    ? `${Key}.${FlattenObjectKeys<Required<T>[Key]>}`
    : `${Key}`
  : never;

export type NonFlattenObjectKeys<
  T extends Record<string, any>,
  Key = keyof T,
> = Key extends string
  ? Required<T>[Key] extends Record<string, any>
    ? never
    : `${Key}`
  : never;

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
