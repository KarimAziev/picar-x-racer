export const speedToReal = (value: number): number => {
  const maxRealSpeed = 2; // in km/h
  const val = (Math.abs(value) / 100) * maxRealSpeed;
  return value > 0 ? val : -val;
};
