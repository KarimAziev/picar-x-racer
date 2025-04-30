import type { Component } from "vue";

export type GetComponentProps<T> = T extends { new (): { $props: infer P } }
  ? P
  : never;

export type Option<T = Component> = {
  label: string;
  value: string;
  convertToValue?: (v: any, prevV: any) => any;
  convertValueOnSwitch?: boolean;
  pred: (v: any) => boolean;
  comp: T;
  props: GetComponentProps<T>;
  tooltip?: string;
};

export function defineComponentOptions<
  Comps extends Record<string, Component>,
  Options extends {
    [K in keyof Comps]: Omit<Option<Comps[K]>, "comp" | "value">;
  },
>(comps: Comps, options: Options): Option[] {
  return Object.keys(options).map((key) => ({
    ...options[key],
    value: key,
    comp: comps[key],
  }));
}

export type CompOption<T = Component> = {
  props: GetComponentProps<T>;
  comp: T;
};

export function defineComponents<
  Comps extends Record<string, Component>,
  P extends keyof Comps,
  PropsOptions extends {
    [K in P as K]: GetComponentProps<Comps[K]>;
  },
  Result extends {
    [K in P as K]: { props: GetComponentProps<Comps[K]>; comp: Comps[K] };
  },
>(comps: Comps, options: PropsOptions): Result {
  return Object.keys(options).reduce((acc, key) => {
    const k = key as P;
    const comp = comps[k];
    const props = options[k];
    acc[k] = {
      comp: comp,
      props: props,
    } as any;
    return acc;
  }, {} as Result);
}
