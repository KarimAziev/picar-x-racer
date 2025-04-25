/**
 * Converts a string to start case (capitalizes the first letter of each word).
 *
 * @param str - The input string to be formatted.
 * @returns The formatted string in start case.
 *
 * @example
 * ```typescript
 * import { startCase } from './util/str';
 *
 * const result1 = startCase("helloWorld");
 * console.log(result1); // "Hello World"
 *
 * const result2 = startCase("snake_case_example");
 * console.log(result2); // "Snake Case Example"
 *
 * const result3 = startCase("  mixed-CASE_string ");
 * console.log(result3); // "Mixed Case String"
 * ```
 */
export const startCase = (str: string) =>
  str
    .trim()
    .replace(/^[_-]+/g, " ")
    .trim()
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[-_]/g, " ")
    .split(" ")
    .map((v) => v[0].toUpperCase() + v.slice(1))
    .join(" ");

export function ensurePrefix(prefix: string): (str: string) => string;
export function ensurePrefix(prefix: string, str: string): string;
export function ensurePrefix(prefix: string, str?: string) {
  return arguments.length === 1
    ? (str: string) => (str.startsWith(prefix) ? str : `${prefix}${str}`)
    : str?.startsWith(prefix)
      ? str
      : str
        ? `${prefix}${str}`
        : str;
}

export const trimSuffix = (str: string, suffix: string) => {
  if (str.endsWith(suffix)) {
    return str.slice(0, -suffix.length);
  }
  return str;
};
