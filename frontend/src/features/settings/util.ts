import { ControllerActionName } from "@/features/controller/store";
import { RemoveFileResponse } from "@/features/settings/interface";
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

export const getBatchFilesErrorMessage = (
  data: RemoveFileResponse[],
  operation: string,
) => {
  const { success, failed } = data.reduce(
    (acc, obj) => {
      const prop = obj.success ? "success" : "failed";
      acc[prop].push(obj);
      return acc;
    },
    {
      success: [] as RemoveFileResponse[],
      failed: [] as RemoveFileResponse[],
    },
  );
  if (failed.length > 0) {
    const prefix =
      success.length > 0
        ? failed.length > 0
          ? `Failed to ${operation} some files: `
          : `Failed to ${operation} the file: `
        : `Failed to ${operation}: `;
    return {
      error: failed.map(({ filename }) => filename).join(", "),
      title: prefix,
    };
  }
};

export const isSelectableModel = (path: string, is_dir?: boolean) => {
  const regex = is_dir ? /_ncnn_model$/ : /\.(?:pt|tflite|onnx|hef)$/;
  return regex.test(path);
};
