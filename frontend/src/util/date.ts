import { DateTime } from "luxon";

export const isDate = (value: any): value is Date => value instanceof Date;

export const toISODateString = (value: string) => {
  return DateTime.fromISO(value).toISO();
};

export const formatDateTimeToIsoString = (date: Date) =>
  DateTime.fromJSDate(date).toFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZZ");

export const isoStringToDateTime = (isoString: string) =>
  DateTime.fromFormat(isoString, "yyyy-MM-dd'T'HH:mm:ss.SSSZZ").toJSDate();
