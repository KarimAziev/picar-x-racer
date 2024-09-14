import { isFunction } from "@/util/guards";

/**
 * @example
 * ```ts
 * const detectors = ["cat", "cat_extended", "human_body", "human_face", null];
 * cycleValue("cat", detectors, 1); // cat_extended
 * cycleValue("human_body", detectors, 1); // human_face
 * cycleValue("human_face", detectors, 1); // null
 * cycleValue(null, detectors, 1); // cat
 * cycleValue(null, detectors, -1); // human_face
 * ```
 */

export const cycleValue = <T>(
  value: (value: T) => boolean | T,
  items: T[],
  direction: number,
): T => {
  const currentIndex = isFunction(value)
    ? items.findIndex(value)
    : items.indexOf(value);

  let newIndex = currentIndex + direction;

  if (newIndex >= items.length) {
    newIndex = newIndex % items.length;
  } else if (newIndex < 0) {
    newIndex = (newIndex + items.length) % items.length;
  }

  return items[newIndex];
};

export const numberSequence = (from: number, to: number, step: number) => {
  const sequence = [];
  for (let i = from; step > 0 ? i <= to : i >= to; i += step) {
    sequence.push(i);
  }
  return sequence;
};
