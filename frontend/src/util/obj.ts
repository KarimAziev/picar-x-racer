import { Narrow } from "@/util/ts-helpers";
import {
  isEmpty,
  isPlainObject,
  isFunction,
  isString,
  isNumber,
} from "@/util/guards";

export const omit = <V extends Record<string, any>, K extends keyof V>(
  props: K[],
  data: V,
): Omit<V, K> => {
  return Object.keys(data).reduce((acc, key) => {
    if (!props.includes(key as K)) {
      acc[key as K] = data[key];
    }
    return acc;
  }, {} as V);
};

export const pickAll = <V extends Record<string, any>, K extends keyof V>(
  props: K[],
  data: V,
): Pick<V, K> => {
  return props.reduce((acc, key) => {
    acc[key as K] = data[key];
    return acc;
  }, {} as V);
};

export const pick = <V extends Record<string, any>, K extends keyof V>(
  props: K[],
  data: V,
): Pick<V, K> => {
  return props.reduce((acc, key) => {
    if (key in data) {
      acc[key as K] = data[key];
    }

    return acc;
  }, {} as V);
};

export const isObjEquals = <V extends Record<string, any>>(
  origData: V,
  newData: V,
) => !isEmpty(diffObjects(origData, newData));

export const formatObj = (obj: Record<string, any>, separator = ", ") =>
  Object.entries(obj)
    .map(([k, v]) => `${k}: ${v}`)
    .join(separator);

/**
 * Represents the evolved type based on the Spec and Target type.
 * Spec type keys are used to transform the corresponding Target type keys.
 * @param Spec - Specification object with transformations to apply.
 * @param Target - Target object to be transformed.
 */

export type Evolve<Spec, Target> = {
  [K in keyof Target]: K extends keyof Spec
    ? /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
      Spec[K] extends (...args: any) => any
      ? ReturnType<Spec[K]>
      : Target[K] extends { [P in keyof Target[K]]?: never }
        ? null
        : Spec[K] extends object
          ? Evolve<Spec[K], Target[K]>
          : Spec[K]
    : Target[K];
};

/**
 * Applies the evolution rules from updateDataMap to the given object recursively.
 * @template Spec - Type specification defining transformation rules.
 * @template Target - Type of the object to evolve.
 * @param updateDataMap - Mapping of transformation functions and values.
 * @param obj - Object to be evolved.
 * @returns - New object with applied transformations.
 */
export function evolve<Spec, Target>(updateDataMap: Narrow<Spec>, obj: Target) {
  /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
  return Object.keys((updateDataMap as any) || {}).reduce(
    (acc, key) => {
      /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
      const updater = (updateDataMap as any)[key as keyof Spec & Target];

      /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
      const value = (obj as Record<any, any>)[key];

      const isObj = isPlainObject(updater);
      const isFunc = isFunction(updater);
      const nextValue =
        !value && (isFunc || isObj)
          ? value
          : isEmpty(value)
            ? null
            : isFunc
              ? updater(value)
              : isObj
                ? evolve(updater, value)
                : updater;

      /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
      (acc as Record<any, any>)[key] = nextValue;

      return acc;
    },
    { ...obj } as Narrow<Evolve<Spec, Target>>,
  );
}

export const reduceObjWith = <
  F extends (...args: any) => any,
  V extends Record<string, unknown>,
  K extends keyof V,
  R extends { [Pattern in K]: ReturnType<F> },
>(
  f: F,
  v: V,
): R => {
  const keys = Object.keys(v) as K[];
  return keys.reduce(
    (acc: R, k: K) => ({
      ...acc,
      [k]: f(v[k]),
    }),
    {} as R,
  );
};

export const diffObjects = <
  V extends Record<string, unknown>,
  B extends Record<string, unknown>,
  O extends V & B,
  K extends keyof O,
>(
  origData: V,
  newData: B,
) => {
  const origKeys = Object.keys(origData);
  const newDataKeys = Object.keys(newData);
  const allKeys = [...newDataKeys, ...origKeys];
  const setKeys = new Set(allKeys);
  const uniqKeys = [...setKeys];

  return uniqKeys.reduce(
    (acc, key) => {
      const newVal = newData[key];
      const origVal = origData[key];

      if (Array.isArray(newVal) && Array.isArray(origVal)) {
        const modifiedItems = newVal.filter((v, i) => {
          if (isPlainObject(v)) {
            const origObj = origVal[i];
            if (!isPlainObject(origObj) || !isEmpty(diffObjects(origObj, v))) {
              return v;
            } else {
              return origVal.includes(v);
            }
          }
        });
        if (!isEmpty(modifiedItems)) {
          (acc as any)[key] = modifiedItems;
        }
      } else if (isPlainObject(newVal) && isPlainObject(origVal)) {
        const modified = diffObjects(origVal, newVal);

        if (!isEmpty(modified)) {
          (acc as any)[key] = modified as Record<string, unknown>;
        }
      } else if (origVal !== newVal) {
        (acc as any)[key] = newVal;
      }

      return acc;
    },
    {} as Partial<{
      [P in K]: O[P] extends Record<string, any> ? Partial<O[P]> : O[P];
    }>,
  );
};

export const formatObjDeep = <Obj extends any>(
  obj: Obj,
  separator = ", ",
  prefix?: string,
): string | undefined => {
  if (isString(obj)) {
    return obj;
  }
  if (isNumber(obj)) {
    return prefix ? `${prefix}: ${obj}` : `${obj}`;
  }
  if (obj === null) {
    return prefix ? `${prefix}: ${null}` : `${null}`;
  }
  if (Array.isArray(obj)) {
    const result = obj
      .map((v) => formatObjDeep(v, separator, prefix))
      .filter(isString);
    if (result.length) {
      return prefix
        ? `${prefix}: ${result.join(separator)}`
        : `${result.join(separator)}`;
    }
  }
  if (isPlainObject(obj)) {
    const result = Object.entries(obj)
      .filter(([_, v]) => v !== undefined)
      .map(([k, res]) =>
        formatObjDeep(res, separator, prefix ? `${prefix}.${k}` : k),
      )
      .filter((v) => isString(v));

    if (result.length === 0) {
      return;
    }

    return `${result.join(separator)}`;
  }
};

export const formatObjectDiff = <
  V extends Record<string, unknown>,
  B extends Record<string, unknown>,
>(
  origData: V,
  newData: B,
) => {
  const diffObj = diffObjects(origData, newData);
  if (!isEmpty(diffObj)) {
    return formatObjDeep(diffObj);
  }
};

export const isObjectEquals = <
  V extends Record<string, unknown>,
  B extends Record<string, unknown>,
>(
  origData: V,
  newData: B,
) => {
  const diffObj = diffObjects(origData, newData);
  return isEmpty(diffObj);
};
