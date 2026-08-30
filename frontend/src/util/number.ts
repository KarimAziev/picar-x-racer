export const roundNumber = (value: number, fractionDigits?: number) => {
  const roundedNumber = value.toFixed(fractionDigits);
  return parseFloat(roundedNumber);
};

export const roundToOneDecimalPlace = (value: number) => roundNumber(value, 1);
export const roundToTwoDecimalPlaces = (value: number) => roundNumber(value, 2);

export const roundToNearest = (value: number, nearestValue: number) =>
  Math.round(value / nearestValue) * nearestValue;
export const roundToNearestTen = (value: number) => roundToNearest(value, 10);

export const generateMultiplesOf32 = (limit: number): number[] => {
  const multiples: number[] = [];
  const stride = 32;

  for (let i = stride; i <= limit; i += stride) {
    multiples.push(i);
  }

  return multiples;
};

export const inRange = (value: number, minValue: number, maxValue: number) =>
  value >= minValue && value <= maxValue;

export const resizeToFit = (
  width: number,
  height: number,
  maxWidth: number,
  maxHeight: number,
): [number, number] => {
  const scaleW = maxWidth / width;
  const scaleH = maxHeight / height;

  const scale = Math.min(scaleW, scaleH);

  const newWidth = Math.round(width * scale);
  const newHeight = Math.round(height * scale);

  return [newWidth, newHeight];
};

export const takePercentage = (value: number, percent: number): number =>
  (value * percent) / 100;

export const parseTrailingNumber = (value: string) => {
  const re = /(\d+)$/;
  const match = value.match(re);
  return match ? +match[1] : null;
};

export function getMaxFractionDigits(step: number) {
  const s = step.toString().toLowerCase();

  if (s.includes("e")) {
    const [base, expStr] = s.split("e");
    const exp = Number(expStr);

    const decimalsInBase = (base.split(".")[1] || "").length;

    if (exp < 0) {
      return decimalsInBase + Math.abs(exp);
    }

    return Math.max(0, decimalsInBase - exp);
  }

  return (s.split(".")[1] || "").length;
}

export const formatDisplayNumber = (value: number): string => {
  const rounded = Math.round(value * 10) / 10;

  if (Number.isInteger(rounded)) {
    return rounded.toString().padStart(2, "0");
  }

  return rounded.toFixed(1);
};
