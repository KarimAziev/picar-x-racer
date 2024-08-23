import { isAxiosError } from "axios";

import { isError } from "@/util/guards";

export const retrieveResponseBody = (error: unknown) => {
  try {
    return JSON.parse((error as any)?.response?.body);
  } catch (err) {
    return error as Error;
  }
};

export const retrieveError = <Err>(error: Err) => {
  if (isAxiosError(error)) {
    return {
      title: error.response?.statusText || "Error",
      text: error.message,
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
