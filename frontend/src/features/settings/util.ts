import { ControllerActionName } from "@/features/controller/store";
import { startCase } from "@/util/str";
import {
  RemoveFileResponse,
  DeviceNode,
  DiscreteDevice,
  DeviceStepwise,
  CameraSettings,
} from "@/features/settings/interface";

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

export type ItemData<Item> = {
  key: string;
  children?: ItemData<Item>[];
} & Item;

export const extractChildren = <DataItem>(
  items: ItemData<DataItem>[],
): DataItem[] => {
  const result: DataItem[] = [];
  const stack = [...items];

  while (stack.length > 0) {
    const current = stack.pop();
    if (current) {
      if (current.children) {
        stack.push(...current.children);
      } else {
        result.push(current);
      }
    }
  }

  return result.reverse();
};

export const mapChildren = <DataItem>(
  items: ItemData<DataItem>[],
  counter = { value: 1 },
): DataItem[] => {
  return items.map((item) => {
    const tabIdx = counter.value++;
    if (item.children) {
      return {
        ...item,
        tabIdx,
        children: mapChildren(item.children, counter),
        selectable: false,
      };
    }
    return {
      ...item,
      tabIdx,
      selectable: true,
    };
  });
};

export const findDevice = (item: CameraSettings, items: DeviceNode[]) => {
  const { device, fps, height, width, pixel_format } = item;
  if (!device || !pixel_format || !width || !height) {
    return;
  }

  const stack: (DeviceStepwise | DeviceNode | DiscreteDevice)[] = [...items];
  const candidates = [];

  while (stack.length > 0) {
    const current = stack.pop();
    if (current) {
      if ((current as any).children) {
        stack.push(...(current as any).children);
      } else if (
        (current as any).pixel_format === pixel_format &&
        (current as any).device === device
      ) {
        if ((current as any).width) {
          const discretedDevice: DiscreteDevice = current as DiscreteDevice;
          if (
            discretedDevice.width === width &&
            discretedDevice.height === height
          ) {
            if (fps === discretedDevice.fps) {
              return discretedDevice;
            } else {
              candidates.push(discretedDevice);
            }
          }
        } else {
          const stepwiseDevice = current as DeviceStepwise;
          if (
            stepwiseDevice.max_width >= width &&
            stepwiseDevice.min_width <= width &&
            stepwiseDevice.max_height >= height &&
            stepwiseDevice.min_height <= height
          ) {
            return stepwiseDevice;
          }
        }
      }
    }
  }

  return candidates[0];
};
