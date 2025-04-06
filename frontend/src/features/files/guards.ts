import {
  FilterFieldStringArray,
  FilterFieldDatetime,
} from "@/features/files/interface";

export const isDateFilter = (item: any): item is FilterFieldDatetime =>
  item && Object.hasOwn(item, "constraints");

export const isFilterFieldStringArray = (
  item: any,
): item is FilterFieldStringArray =>
  item &&
  !isDateFilter(item) &&
  Object.hasOwn(item, "value") &&
  Object.hasOwn(item, "match_mode");
