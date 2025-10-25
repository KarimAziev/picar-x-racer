import { compareByLength } from "@/util/func";

export const uniq = <T>(items: T[]) => Array.from(new Set(items));

export const takeWhile = <T>(items: T[], pred: (arg: T) => boolean) => {
  const result: T[] = [];
  for (const item of items) {
    if (!pred(item)) break;
    result.push(item);
  }
  return result;
};

export function sortByLengthAsc<T extends { length?: number }>(
  items: T[],
): T[] {
  return [...items].sort(compareByLength);
}
