import { cloneDeep } from "@/util/obj";
import { isRef } from "vue";
import { isPlainObject } from "@/util/guards";

const formatObj = (obj: any) =>
  isPlainObject(obj) || Array.isArray(obj) ? cloneDeep(obj) : obj;

export const log = (...args: any[]) => {
  const mappedArgs = args.map((a) => formatObj(isRef(a) ? a.value : a));
  console.log.apply(null, mappedArgs);
};
