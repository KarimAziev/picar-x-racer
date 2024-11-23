export const omit = <V extends Record<string, any>, K extends keyof V>(
  props: K[],
  data: V,
): Omit<V, K> => {
  return Object.keys(data).reduce((acc, key) => {
    if (!props.includes(key as K)) {
      acc[key as K] = data[key];
    }
    return acc;
  }, {} as V);
};

export const pickAll = <V extends Record<string, any>, K extends keyof V>(
  props: K[],
  data: V,
): Pick<V, K> => {
  return props.reduce((acc, key) => {
    acc[key as K] = data[key];
    return acc;
  }, {} as V);
};

export const pick = <V extends Record<string, any>, K extends keyof V>(
  props: K[],
  data: V,
): Pick<V, K> => {
  return props.reduce((acc, key) => {
    if (key in data) {
      acc[key as K] = data[key];
    }

    return acc;
  }, {} as V);
};
