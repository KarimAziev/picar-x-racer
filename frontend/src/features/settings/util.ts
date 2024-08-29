import { ControllerActionName } from "@/features/controller/store";
import { startCase } from "@/util/str";

export const objectKeysToOptions = (
  obj: Record<string, string[]>,
  labelsMap?: Record<string, string>,
) =>
  Object.keys(obj).map((c) => ({
    value: c,
    label: (labelsMap && labelsMap[c]) || startCase(c),
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
