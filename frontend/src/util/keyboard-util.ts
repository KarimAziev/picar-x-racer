import { KeyboardMapper } from "../util/keyboard-mapper";

export interface KeyEventItem {
  key: string;
  ctrlKey: boolean;
  shiftKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  code?: string;
}

/**
 * Splits a string while preserving consecutive separators as distinct elements.
 * @param str - String to split.
 * @param separators - Characters to use as separators.
 * @returns Array of strings, split according to the given separators.
 */
export function splitPreservingConsecutiveSeparators(
  str: string,
  separators: string[],
): string[] {
  const dictSet = new Set<string>(separators);

  if (dictSet.has(str)) {
    return [str];
  }

  let result: string[] = [];

  let buffer = "";
  let i = 0;

  while (i < str.length) {
    const char = str[i];
    const nextChar = i + 1 < str.length && str[i + 1];
    const isSeparator = dictSet.has(char);

    if (isSeparator && nextChar === char) {
      if (buffer.length > 0) {
        result.push(buffer);
        buffer = "";
      }
      result.push(str[i]);

      i += 2;
    } else if (!isSeparator) {
      buffer += str[i++];
    } else {
      if (buffer.length > 0) {
        result.push(buffer);
        buffer = "";
      }
      i++;
    }
  }

  if (buffer.length > 0) {
    result.push(buffer);
  }

  return result;
}

/**
 * Splits a keyboard shortcut sequence into its component parts while compensating for spaces.
 * @param str - The keyboard shortcut sequence.
 * @returns Array of the split sequence.
 */
export const splitKeySequence = (str: string): string[] =>
  splitPreservingConsecutiveSeparators(
    str
      .replace(/(^|\s|-)(space|spc)(?=$)/gi, " space ")
      .replace(/(^)(space|spc)(?=$|\s|-)/gi, " space")
      .replace(/(^|\s|-)(space|spc)(?=$|\s|-)/gi, "$1 "),
    ["-", " "],
  );

/**
 * Parses a key sequence string into an array of KeyEventItem.
 * @param sequence - The key sequence to parse.
 * @returns Array of KeyEventItem corresponding to the keys in the sequence.
 */
export function parseKeySequence(sequence: string): KeyEventItem[] {
  const chars = splitKeySequence(sequence).reverse();

  const result: KeyEventItem[] = [];
  let currKey: string;
  let lastMods: ("ctrl" | "shift" | "meta" | "alt")[] = [];
  while (chars.length > 0) {
    currKey = chars.pop() as string;
    if (KeyboardMapper.isModifier(currKey)) {
      const alias = KeyboardMapper.isCtrlKey(currKey)
        ? "ctrl"
        : KeyboardMapper.isShiftKey(currKey)
          ? "shift"
          : KeyboardMapper.isMetaKey(currKey)
            ? "meta"
            : KeyboardMapper.isAltKey(currKey)
              ? "alt"
              : null;
      if (!alias || lastMods.includes(alias)) {
        return [];
      } else {
        lastMods.push(alias);
      }
    } else {
      const evData = {
        key: currKey,
        ctrlKey: lastMods.includes("ctrl"),
        metaKey: lastMods.includes("meta"),
        altKey: lastMods.includes("alt"),
        shiftKey:
          lastMods.includes("shift") ||
          (currKey.length === 1 && /^[A-Z]$/.test(currKey)),
      };

      lastMods = [];
      result.push(evData);
    }
  }

  return result;
}

/**
 * Formats a single KeyEventItem into a human-readable string.
 * @param curr - The KeyEventItem to format.
 * @param separator - The separator to use between keys and modifiers.
 * @returns A string representing the KeyEventItem.
 */
export function formatKeyEventItem(
  curr: KeyEventItem,
  separator = "-",
): string {
  const realKey = translateKeyboardEventToKey(curr);
  if (!realKey) {
    return "";
  }
  const isUpcased = realKey.length === 1 && /^[A-Z]$/.test(realKey);

  const keyReplacementMap: { [k: KeyEventItem["key"]]: string } = {
    " ": "Space",
  };

  const labels = {
    ctrlKey: "Ctrl",
    metaKey: "Meta",
    altKey: "Alt",
    shiftKey: isUpcased ? null : "Shift",
  };

  const metaKeys = Object.entries(labels).flatMap(([prop, val]) =>
    curr[prop as keyof typeof curr] && val ? [val] : [],
  );

  const label = metaKeys
    .concat([keyReplacementMap[realKey] || realKey])
    .join(separator);
  return label;
}

/**
 * Formats an array of KeyEventItems into a concise key sequence string.
 * @param keyEvents - Array of KeyEventItem to format.
 * @param separator - The separator to use between keys and modifiers.
 * @returns A string representing the sequence of KeyEventItems.
 */
export function formatKeyboardEvents(
  keyEvents: KeyEventItem[],
  separator = "-",
): string {
  return keyEvents
    .reduce((acc, curr) => {
      const label = formatKeyEventItem(curr, separator);
      acc.push(label);
      return acc;
    }, [] as string[])
    .join(" ")
    .replace(/^Shift-/g, "");
}

/**
 * Validates a string as a potential key sequence by parsing and ensuring it ends with a key.
 * @param keystr - The key sequence string to validate.
 * @returns true if the string is a valid key sequence, false otherwise.
 */
export function validateKeyString(keystr: string): boolean {
  const evs = parseKeySequence(keystr);

  const lastKey = evs.pop();

  return !!lastKey?.key;
}

export const translateKeyboardEventToKey = (
  event: Pick<KeyEventItem, "code" | "key">,
) => {
  const { key, code } = event;
  if (key && KeyboardMapper.nonModifiersConfig[key]) {
    return key;
  }
  const props = code && KeyboardMapper.nonModifiersConfig[code];
  return props ? props.key : key;
};
splitKeySequence("ff");
