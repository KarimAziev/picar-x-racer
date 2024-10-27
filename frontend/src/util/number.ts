export const roundNumber = (value: number, fractionDigits?: number) => {
  const roundedNumber = value.toFixed(fractionDigits);
  return parseFloat(roundedNumber);
};

export const roundToNearestTen = (value: number) => Math.round(value / 10) * 10;
