import { isAxiosError } from "axios";

import {
  isArray,
  isError,
  isNumber,
  isPlainObject,
  isString,
} from "@/util/guards";

export const retrieveResponseBody = (error: unknown) => {
  try {
    return JSON.parse((error as any)?.response?.body);
  } catch (err) {
    return error as Error;
  }
};

const stringifyError = (data: any): string => {
  if (isString(data)) {
    return data;
  }
  if (isNumber(data)) {
    return `${data}`;
  }
  if (isArray(data)) {
    return data.map(stringifyError).join("\n");
  }
  if (isPlainObject(data)) {
    return Object.entries(data)
      .map(([key, value]) => {
        const str = `${key}: ${stringifyError(value)}`;
        return str;
      })
      .join("\n");
  }
  return "";
};

export const retrieveError = <Err>(error: Err) => {
  if (isAxiosError(error)) {
    const data = error.response?.data;

    return {
      title: error.response?.statusText
        ? `${error.response?.statusText}: `
        : "",
      text: stringifyError(
        data?.detail || data?.error || data || error.message,
      ),
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
