export type MethodsWithoutParams<T> = {
  [K in keyof T as T[K] extends (...args: infer P) => any
    ? P extends []
      ? K
      : never
    : never]: T[K] extends (...args: infer _P) => any ? T[K] : never;
};
