export const roundNumber = (value: number, fractionDigits?: number) => {
  const roundedNumber = value.toFixed(fractionDigits);
  return parseFloat(roundedNumber);
};

export const roundToOneDecimalPlace = (value: number) => roundNumber(value, 1);

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
