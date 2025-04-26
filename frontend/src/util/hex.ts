import { isString } from "@/util/guards";

export const isHexString = (value?: string) =>
  isString(value) && /^0x/i.test(value);

export function hexToDecimal(hexString: string) {
  if (!/^0x/i.test(hexString)) {
    return null;
  }

  const result = parseInt(hexString, 16);

  if (isNaN(result)) {
    return null;
  }

  return result;
}

export function decimalToHexString(decimal: number) {
  if (typeof decimal !== "number" || !Number.isFinite(decimal)) {
    return null;
  }

  return "0x" + decimal.toString(16);
}
