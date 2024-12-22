import { ControllerActionName } from "@/features/controller/store";
import { startCase } from "@/util/str";
import { RemoveFileResponse } from "@/features/settings/interface";

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

export const getBatchFilesErrorMessage = (data: RemoveFileResponse[]) => {
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
          ? "Failed to remove some files: "
          : "Failed to remove the file: "
        : "Failed to remove: ";
    return {
      error: failed.map(({ filename }) => filename).join(", "),
      title: prefix,
    };
  }
};
