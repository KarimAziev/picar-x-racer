/**
 * Constrains a value to lie between a minimum and maximum value.
 *
 * @param minValue - The minimum value.
 * @param maxValue - The maximum value.
 * @param value - The value to constrain.
 * @returns The constrained value.
 */
export const constrain = (minValue: number, maxValue: number, value: number) =>
  Math.min(Math.max(value, minValue), maxValue);
