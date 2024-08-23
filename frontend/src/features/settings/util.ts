import { ControllerActionName } from "@/features/controller/store";

export const READONLY_KEY = "Escape";

export const objectKeysToOptions = (
  obj: Record<string, string[]>,
  labelsMap?: Record<string, string>,
) =>
  Object.keys(obj).map((c) => ({
    value: c,
    label:
      (labelsMap && labelsMap[c]) ||
      c
        .trim()
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .split(" ")
        .map((v) => v[0].toUpperCase() + v.slice(1))
        .join(" "),
  }));

export const groupKeys = (data: Record<ControllerActionName, string[]>) =>
  Object.entries(data).reduce(
    (acc, [command, keys]) => {
      keys.forEach((k) => {
        acc[k] = command as ControllerActionName;
      });
      return acc;
    },
    {} as Record<string, ControllerActionName>,
  );
