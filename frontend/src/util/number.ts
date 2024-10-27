export const roundNumber = (value: number, fractionDigits?: number) => {
  const roundedNumber = value.toFixed(fractionDigits);
  return parseFloat(roundedNumber);
};
