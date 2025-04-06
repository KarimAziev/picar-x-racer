import { ControllerActionName } from "@/features/controller/store";
import { startCase } from "@/util/str";

export const objectKeysToOptions = (
  obj: Record<string, string[]> | string[],
  labelsMap?: Record<string, string>,
) =>
  (Array.isArray(obj) ? obj : Object.keys(obj)).map((c) => ({
    value: c,
    label: (labelsMap && labelsMap[c]) || startCase(c),
  }));

export const groupKeys = (
  data: Partial<Record<ControllerActionName, string[] | null>>,
) =>
  Object.entries(data).reduce(
    (acc, [command, keys]) => {
      if (keys) {
        keys.forEach((k) => {
          acc[k] = command as ControllerActionName;
        });
      }
      return acc;
    },
    {} as Record<string, ControllerActionName>,
  );

export const isSelectableModel = (path: string, is_dir?: boolean) => {
  const regex = is_dir ? /_ncnn_model$/ : /\.(?:pt|tflite|onnx|hef)$/;
  return regex.test(path);
};
