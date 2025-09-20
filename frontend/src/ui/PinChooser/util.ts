import type {
  PinMapping,
  PinSchema,
  PinInfoNormalized,
} from "@/features/pinout/store";
import type { ValueLabelOption } from "@/types/common";
import { isNil } from "@/util/guards";
import { groupBy } from "@/util/obj";
import {
  commonPinsLayoutDescriptions,
  powerLabels,
} from "@/features/pinout/config";

/**
 * Try to parse a pin name into { prefix, number } when it represents a "prefix+number" style label.
 * Handles:
 *  - "J8:1"  -> { prefix: "J8", num: "1" }
 *  - "BOARD1" -> { prefix: "BOARD", num: "1" }
 *  - "GPIO17" -> { prefix: "GPIO", num: "17" }
 *  - "WPI8" -> { prefix: "WPI", num: "8" }
 * Rejects things like "3V3" (starts with digit, not a layout), "GND", "5V" (no trailing numeric index in conventional sense).
 */
export const parsePrefixNumber = (
  raw: string,
): { prefix: string; num: string } | null => {
  if (!raw) return null;
  const s = String(raw).trim();

  // If there's a colon, treat left of colon as prefix and require right side be digits.
  const colonIdx = s.indexOf(":");
  if (colonIdx !== -1) {
    const left = s.slice(0, colonIdx).trim();
    const right = s.slice(colonIdx + 1).trim();

    if (/^\d+$/.test(right) && left.length > 0) {
      return { prefix: left.toUpperCase(), num: right };
    }
    return null;
  }

  // Otherwise match letter-start prefix + trailing digits (BOARD1, BCM17, GPIO2)
  const m = s.match(/^([A-Za-z][A-Za-z0-9]*?)(\d+)$/);
  if (m) {
    return { prefix: m[1].toUpperCase(), num: m[2] };
  }

  return null;
};

export const pinValueLayout = (
  options: ValueLabelOption[],
  value?: string | null,
) => {
  if (isNil(value)) {
    return;
  }
  const parsed = parsePrefixNumber(value);
  if (parsed) {
    const result = options.find((opt) => opt.value === parsed.prefix)?.value;
    console.log("result", result, "options", options);
    return result;
  }
};

export const normalizePins = (mapping: PinMapping) => {
  const allPins: PinSchema[] = Object.values(mapping).reduce(
    (acc, { pins }) => acc.concat(Object.values(pins)),
    [] as PinSchema[],
  );

  const layoutsMap = new Map<
    string,
    { count: number; numbers: Set<string>; samples: string[] }
  >();

  const hash = new Map<string | number, PinInfoNormalized>();

  allPins.forEach((pin) => {
    const isGpio = !isNil(pin.gpio_number);

    const layouts: Record<string, string> = {};

    pin.names.forEach((name) => {
      const parsed = parsePrefixNumber(name);
      if (!parsed) {
        return;
      }

      const key = parsed.prefix;
      layouts[key] = name;

      if (!isGpio) {
        return;
      }

      const entry = layoutsMap.get(key) ?? {
        count: 0,
        numbers: new Set<string>(),
        samples: [],
      };
      entry.count += 1;
      entry.numbers.add(parsed.num);
      entry.samples.push(String(name));
      layoutsMap.set(key, entry);
    });

    const mappedPin = { ...pin, selectable: isGpio, layouts };

    if (isGpio) {
      hash.set(pin.gpio_number as number, mappedPin);
    }
    mappedPin.names.forEach((name) => {
      if (!powerLabels[name] && !hash.get(name)) {
        hash.set(name, { ...mappedPin, name });
      }
    });
  });

  return {
    hash,
    layoutOptions: Array.from(layoutsMap).map(([k, v]) => ({
      value: k,
      label: commonPinsLayoutDescriptions[k] || k,
      count: v.count,
    })),
  };
};

export function groupColumnsSorted(pinsObj: Record<string, PinSchema>) {
  const groups = groupBy("col", Object.values(pinsObj));

  return Object.entries(groups)
    .sort(([a1], [a2]) => +a1 - +a2)
    .map(([_, val]) => val.sort((a, b) => a.row - b.row));
}
