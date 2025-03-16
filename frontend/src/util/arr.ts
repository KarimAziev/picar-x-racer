export const uniq = <T>(items: T[]) => Array.from(new Set(items));

export const takeWhile = <T>(items: T[], pred: (arg: T) => boolean) => {
  const result: T[] = [];
  for (const item of items) {
    if (!pred(item)) break;
    result.push(item);
  }
  return result;
};
