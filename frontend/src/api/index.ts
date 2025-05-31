import { APIClient } from "@/api/apiCient";
import { makeUrl } from "@/util/url";
import { isString } from "@/util/guards";

export const appApi = APIClient.make(
  makeUrl(
    "/",
    isString(import.meta.env.VITE_MAIN_APP_PORT)
      ? +import.meta.env.VITE_MAIN_APP_PORT
      : undefined,
  ),
);
export const robotApi = APIClient.make(
  makeUrl("/", +(import.meta.env.VITE_WS_APP_PORT || "8001")),
);
