import type {
  DataTableFilterMeta,
  DataTableOperatorFilterMetaData,
} from "primevue/datatable";
import { isString } from "@/util/guards";

/**
 * Type guard that checks whether a PrimeVue DataTable filter entry is a
 * "date/operator" filter object (i.e. has `constraints`).
 *
 * @param value - A filter meta value from PrimeVue DataTable.
 * @returns True if the value is an operator filter meta data object.
 */
export const isDateFilter = (
  value: DataTableFilterMeta[keyof DataTableFilterMeta],
): value is DataTableOperatorFilterMetaData =>
  !isString(value) &&
  "constraints" in value &&
  Array.isArray(value.constraints);
