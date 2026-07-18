import { isProxy, isRef, unref, toRaw } from "vue";
import type { MaybeRef, ComputedRef } from "vue";
import { isPlainObject, isObjectLike } from "@/util/guards";

type Seen = WeakMap<object, any>;

function deepUnwrap<T>(
  value: MaybeRef<T> | ComputedRef<T>,
  seen: Seen = new WeakMap(),
): T {
  const v = (isRef(value) ? unref(value) : value) as T;

  if (!isObjectLike(v)) {
    return v;
  }

  const raw = isProxy(v) ? toRaw(v) : v;

  if (seen.has(raw)) {
    return seen.get(raw);
  }

  if (Array.isArray(raw)) {
    const out: any[] = [];
    seen.set(raw, out);
    for (const item of raw) {
      out.push(deepUnwrap(item, seen));
    }
    return out as T;
  }

  if (raw instanceof Date) {
    return new Date(raw.getTime()) as T;
  }

  if (raw instanceof RegExp) {
    return new RegExp(raw) as T;
  }

  if (raw instanceof Map) {
    const out = new Map();
    seen.set(raw, out);
    for (const [k, val] of raw.entries()) {
      out.set(deepUnwrap(k, seen), deepUnwrap(val, seen));
    }
    return out as T;
  }

  if (raw instanceof Set) {
    const out = new Set();
    seen.set(raw, out);
    for (const item of raw.values()) {
      out.add(deepUnwrap(item, seen));
    }
    return out as T;
  }

  if (isPlainObject(raw)) {
    const out: Record<string, unknown> = {};
    seen.set(raw, out);
    for (const [k, val] of Object.entries(raw)) {
      out[k] = deepUnwrap(val, seen);
    }
    return out as T;
  }

  return raw;
}

export function cloneForLog<T>(value: T): T {
  const unwrapped = deepUnwrap(value);

  try {
    return structuredClone(unwrapped);
  } catch {
    return unwrapped;
  }
}

const formatObj = <T>(obj: T) =>
  isPlainObject(obj) || Array.isArray(obj) || isRef(obj)
    ? cloneForLog(obj)
    : obj;

export const log = (...args: any[]) => {
  const mappedArgs = args.map(formatObj);

  console.log(...mappedArgs);
};
