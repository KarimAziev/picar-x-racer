import {
  Narrow,
  FlattenObject,
  ExtractStringPropsKey,
} from "@/util/ts-helpers";
import {
  isEmpty,
  isPlainObject,
  isFunction,
  isString,
  isNumber,
  isSymbol,
  isBigint,
  isBoolean,
  isArray,
  isNull,
  isUndefined,
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

export const props = <V extends Record<string, any>, K extends keyof V>(
  props: K[],
  data: V,
): V[K][] => props.map((key) => data[key]);

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

export function cloneDeep<T>(value: T): T {
  if (value === null || value === undefined) {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map((item) => cloneDeep(item)) as unknown as T;
  }

  if (typeof value === "object") {
    const clonedObj: Record<string, any> = {};
    for (const key in value) {
      if (Object.prototype.hasOwnProperty.call(value, key)) {
        clonedObj[key] = cloneDeep((value as Record<string, any>)[key]);
      }
    }
    return clonedObj as T;
  }

  return value;
}

export const formatObjDeep = <Obj extends any>(
  obj: Obj,
  separator = ", ",
  prefix?: string,
): string | undefined => {
  if (obj === undefined || isEmpty(obj)) {
    return;
  }
  if (Array.isArray(obj)) {
    const result = obj
      .map((v) => formatObjDeep(v, separator, prefix))
      .filter(isString);
    if (result.length) {
      return `${result.join(separator)}`;
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
  return prefix ? `${prefix}: ${obj}` : `${obj}`;
};

export const formatObjectDiff = <
  V extends Record<string, unknown>,
  B extends Record<string, unknown>,
>(
  origData: V,
  newData: B,
) => {
  const a = cloneDeep(origData);
  const b = cloneDeep(newData);
  const diffObj = diffObjectsDeep(a, b);

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
  const diffObj = diffObjectsDeep(origData, newData);

  return !diffObj || isEmpty(diffObj);
};

export const diffObjectsDeep = <
  OrigObj extends Record<string, any>,
  NewObj extends Record<string, any>,
>(
  orig: OrigObj,
  updated: NewObj,
): Partial<NewObj> | NewObj[] | undefined => {
  const visited = new WeakSet();
  const primitivesFns = [
    isString,
    isNumber,
    isUndefined,
    isNull,
    isBoolean,
    isBigint,
    isSymbol,
    isFunction,
  ];

  const noDiffs = Symbol("nodiffs");
  type ResultType = Partial<NewObj> | NewObj[] | typeof noDiffs;

  const worker = <OrigData, NewData = OrigData>(
    origData: OrigData,
    newData: NewData,
  ): ResultType => {
    if (primitivesFns.some((fn) => fn(origData) || fn(newData))) {
      return origData === (newData as unknown as OrigData)
        ? noDiffs
        : (newData as ResultType);
    }

    const isOrigArray = isArray(origData);
    const isNewArray = isArray(newData);

    if (isOrigArray || isNewArray) {
      if (!isOrigArray || !isNewArray) {
        return newData as ResultType;
      }

      if (origData.length > newData.length) {
        return newData;
      }

      const diffs = (newData as any[]).flatMap((v, i) => {
        if (
          !isPlainObject(v) &&
          !isArray(v) &&
          origData.some((val) => {
            visited.delete(val);
            visited.delete(v);
            const r = worker(val, v);
            return r === noDiffs;
          })
        ) {
          return [];
        }
        if (i > (origData as any[]).length - 1) {
          return [v];
        }

        visited.delete(origData[i]);
        visited.delete(v);
        const changes = worker((origData as any[])[i], v);

        return changes === noDiffs ? [] : [changes];
      });

      return isEmpty(diffs) ? noDiffs : diffs;
    }

    const isOrigObject = isPlainObject(origData);
    const isNewObject = isPlainObject(newData);

    if (isOrigObject || isNewObject) {
      if (!isOrigObject || !isNewObject) {
        return newData as ResultType;
      }

      if (visited.has(origData as object) || visited.has(newData as object)) {
        return noDiffs;
      }
      visited.add(origData as object).add(newData as object);

      const origKeys = Object.keys(origData);
      const newDataKeys = Object.keys(newData).filter(
        (k) => !origKeys.includes(k),
      );
      const allKeys = [...newDataKeys, ...origKeys];

      const diffs = allKeys.reduce(
        (acc, key) => {
          const origVal = (origData as Record<string, any>)[key];
          const newVal = (newData as Record<string, any>)[key];

          const changes = worker(origVal, newVal);
          if (changes !== noDiffs) {
            acc[key] = changes;
          }
          return acc;
        },
        {} as Record<string, any>,
      );

      return isEmpty(diffs) ? noDiffs : (diffs as ResultType);
    }
    return newData as ResultType;
  };

  const result = worker(orig, updated);
  return result === noDiffs ? undefined : result;
};

export const getObjProp = <
  Obj extends Record<string, any>,
  Key extends keyof FlattenObject<Obj>,
  Result extends FlattenObject<Obj>[Key],
>(
  key: Key,
  obj: Obj,
): Result => {
  const paths = key.split(".");
  const result = paths.reduce((acc, path) => acc?.[path], obj as any);

  return result as Result;
};

export const setObjProp = <
  Obj extends Record<string, any>,
  Key extends keyof FlattenObject<Obj>,
  Value,
>(
  obj: Obj,
  key: Key,
  value: Value extends FlattenObject<Obj>[Key] ? Value : never,
): Obj => {
  const paths = key.split(".");

  const lastKey = paths.pop();
  const target = paths.reduce((acc, path) => acc?.[path], obj as any);

  if (lastKey !== undefined) {
    target[lastKey] = value;
  }
  return obj;
};

export function splitObjIntoGroups(
  count: number,
  obj: Record<string, any>,
): Record<string, any>[] {
  const keys = Object.keys(obj);
  const values = Object.values(obj);
  const result: Record<string, any>[] = Array.from(
    { length: count },
    () => ({}),
  );

  keys.forEach((key, index) => {
    const groupIndex = index % count;
    result[groupIndex][key] = values[index];
  });

  return result;
}

export const groupBy = <
  Obj extends Record<string, any>,
  Prop extends ExtractStringPropsKey<Obj>,
>(
  propName: Prop,
  objs: Obj[],
) =>
  objs.reduce(
    (acc, obj) => {
      const key = obj[propName];

      if (!acc[key]) {
        acc[key] = [obj] as Obj[];
      } else {
        acc[key].push(obj);
      }

      return acc;
    },
    {} as Record<Obj[Prop], Obj[]>,
  );

export const groupWith = <
  Obj extends Record<string, any>,
  Prop extends ExtractStringPropsKey<Obj>,
  Fn extends (obj: Obj) => any,
>(
  propName: Prop,
  fn: Fn,
  objs: Obj[],
) =>
  objs.reduce(
    (acc, obj) => {
      const key = obj[propName];
      const transformed = fn(obj);

      if (!acc[key]) {
        acc[key] = [transformed];
      } else {
        acc[key].push(transformed);
      }

      return acc;
    },
    {} as Record<Obj[Prop], ReturnType<Fn>[]>,
  );

export const isObjectShallowEquals = <
  V extends Record<string, unknown>,
  B extends Record<string, unknown>,
>(
  origData: V,
  newData: B,
) => {
  const origEntries = Object.entries(origData);

  if (origEntries.length !== Object.keys(newData).length) {
    return false;
  }

  return origEntries.every(([key, value]) => value === newData[key]);
};
