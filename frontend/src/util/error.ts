import { isAxiosError } from "axios";

import {
  isArray,
  isError,
  isNumber,
  isPlainObject,
  isString,
  anyPass,
} from "@/util/guards";
import { where } from "@/util/func";

export const retrieveResponseBody = (error: unknown) => {
  try {
    return JSON.parse((error as any)?.response?.body);
  } catch (err) {
    return error as Error;
  }
};

export const validationErrorPred = where({
  loc: (x: unknown) => Array.isArray(x) && x.every(anyPass(isString, isNumber)),
  msg: isString,
  type: isString,
});

const formatLoc = (loc: Array<string | number>) =>
  loc
    .filter((part) => part !== "body" && part !== "query" && part !== "path")
    .join(".");

const stringifyError = (data: unknown): string => {
  if (isString(data)) return data;
  if (isNumber(data)) return String(data);

  if (isArray(data)) {
    return data
      .map((item) => {
        if (validationErrorPred(item)) {
          const path = formatLoc(item.loc);
          return path ? `${path}: ${item.msg}` : item.msg;
        }
        return stringifyError(item);
      })
      .filter(Boolean)
      .join("\n");
  }

  if (isPlainObject(data)) {
    if (validationErrorPred(data)) {
      const path = formatLoc(data.loc);
      return path ? `${path}: ${data.msg}` : data.msg;
    }

    if ("detail" in data) {
      return stringifyError((data as any).detail);
    }

    if ("error" in data) {
      return stringifyError((data as any).error);
    }

    return Object.entries(data)
      .map(([key, value]) => `${key}: ${stringifyError(value)}`)
      .join("\n");
  }

  return "";
};

export const retrieveError = <Err>(error: Err) => {
  if (isAxiosError(error)) {
    const data = error.response?.data;

    const text = stringifyError(
      data?.detail || data?.error || data || error.message,
    );

    return {
      title: error.response?.statusText
        ? `${error.response?.statusText}: `
        : "",
      text: text,
    };
  }

  if (isError(error)) {
    return {
      title: "Error",
      text: error.message,
    };
  } else {
    return {
      title: "Error",
      text: (error as Error)?.message || "An error occured",
    };
  }
};
