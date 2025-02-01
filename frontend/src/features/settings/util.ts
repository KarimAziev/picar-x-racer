import { ControllerActionName } from "@/features/controller/store";
import { startCase } from "@/util/str";
import {
  RemoveFileResponse,
  DeviceNode,
  DiscreteDevice,
  DeviceStepwise,
  CameraSettings,
  StepwiseDeviceProps,
  GstreamerDiscreteDevice,
  GstreamerStepwiseDevice,
  Device,
} from "@/features/settings/interface";
import { props } from "@/util/obj";
import { isNumber } from "@/util/guards";
import { inRange } from "@/util/number";

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

export const extractDeviceId = (path?: string) => {
  if (!path) {
    return path;
  }

  const parts = path.split(":");
  if (parts.length > 1 && parts.shift()) {
    return parts.join(":");
  }
  return path;
};

const checkPixelFormat = (a?: string, b?: string) => a === b || (!a && !b);

export const findDevice = (item: CameraSettings, items: DeviceNode[]) => {
  const { device, fps, height, width, pixel_format } = item;
  if (!device || !width || !height) {
    return;
  }

  const stack: (DeviceStepwise | DeviceNode | DiscreteDevice)[] = [...items];
  const candidates: DiscreteDevice[] = [];

  while (stack.length > 0) {
    const current = stack.pop();
    if (current) {
      const currDevice = (current as any).device;

      if ((current as any).children) {
        stack.push(...(current as any).children);
      } else if (
        extractDeviceId(device) === extractDeviceId(currDevice) &&
        checkPixelFormat(pixel_format, (current as any).pixel_format)
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

export const validateStepwiseData = (
  stepWiseDevice: StepwiseDeviceProps,
  data: Pick<CameraSettings, "fps" | "width" | "height">,
) => {
  if (!stepWiseDevice) {
    return {};
  }
  return Object.entries(data).reduce(
    (acc, [k, val]) => {
      const key = k as keyof typeof data;
      const stepKey = `${key}_step` as const;
      const minVal = stepWiseDevice[`min_${key}`];
      const maxVal = stepWiseDevice[`max_${key}`];
      const step =
        key === "fps"
          ? 1
          : stepWiseDevice[stepKey as Exclude<typeof stepKey, "fps_step">];
      if (!isNumber(val)) {
        acc[key] = "Required";
      } else if (
        isNumber(minVal) &&
        isNumber(maxVal) &&
        !inRange(val, minVal, maxVal)
      ) {
        acc[key] = `Should be between ${minVal} and ${maxVal}`;
      } else if (
        isNumber(minVal) &&
        isNumber(maxVal) &&
        step &&
        (val - minVal) % step !== 0
      ) {
        const closestValidValue = Math.min(
          maxVal,
          Math.max(minVal, minVal + Math.round((val - minVal) / step) * step),
        );
        acc[key] =
          `Invalid step. The closest valid value is ${closestValidValue}.`;
      }

      return acc;
    },
    {} as Record<keyof typeof data, string>,
  );
};

export const isStepwiseDeviceStrict = (data: any): data is DeviceStepwise =>
  data.max_width && data.pixel_format && !data.media_type;

export const isDiscreteDevice = (data: any): data is DiscreteDevice =>
  data.width && data.pixel_format && !data.media_type;

export const isGstreamerStepwiseDevice = (
  data: any,
): data is GstreamerStepwiseDevice => data.max_width && data.media_type;

export const isGstreamerDiscreteDevice = (
  data: any,
): data is GstreamerDiscreteDevice => data.width && data.media_type;

export const isStepwiseDevice = (data: any): data is DeviceStepwise =>
  data?.max_width;

export const generateLabel = (device: Device) => {
  const isGstreamerStepwise = isGstreamerStepwiseDevice(device);

  if (isGstreamerStepwiseDevice(device) || isStepwiseDeviceStrict(device)) {
    const minSize = props(["min_width", "min_height"], device).join("x");
    const maxSize = props(["max_width", "max_height"], device).join("x");
    const fps = props(["min_fps", "max_fps"], device)
      .map((v) => `${v}`)
      .join("-")
      .concat("FPS");
    const size = `${minSize} - ${maxSize}`;
    return [
      device.pixel_format,
      size,
      fps,
      isGstreamerStepwise ? device.media_type : null,
    ]
      .filter((val) => !!val)
      .map((v) => `${v}`)
      .join(" ");
  }
  const size = props(["width", "height"], device).join("x");
  return [
    device.pixel_format,
    size,
    device.fps ? `${device.fps}FPS` : device.fps,
    isGstreamerDiscreteDevice(device) ? device.media_type : null,
  ]
    .filter((val) => !!val)
    .map((v) => `${v}`)
    .join(" ");
};

export const groupDevices = (devices: Device[]): DeviceNode[] => {
  const deviceMap: { [key: string]: DeviceNode } = {};

  for (const device of devices) {
    const deviceKey = extractDeviceId(device.device);

    if (!deviceKey) {
      continue;
    }
    if (!deviceMap[deviceKey]) {
      deviceMap[deviceKey] = {
        key: deviceKey,
        label: [deviceKey, device.name].filter((v) => !!v).join(" "),
        children: [],
      };
    }

    const root = deviceMap[deviceKey];

    const pixelFormat: string =
      device.pixel_format || (device as any).media_type;

    const childLabel = generateLabel(device);

    const childKey = `${deviceKey}:${childLabel}`;

    if (!pixelFormat) {
      root.children.push({ ...device, key: childKey, label: childLabel });
      continue;
    }
    const pixelFormatKey = `${deviceKey}:${pixelFormat}`;

    let pixelFormatNode = root.children.find(
      (child) => (child as DeviceNode).key === pixelFormatKey,
    ) as DeviceNode;

    if (!pixelFormatNode) {
      pixelFormatNode = {
        key: pixelFormatKey,
        label: pixelFormat,
        children: [],
      };
      root.children.push(pixelFormatNode);
    }

    pixelFormatNode.children.push({
      key: childKey,
      label: childLabel,
      ...device,
    });
  }

  return Object.values(deviceMap);
};
