import { ControllerActionName } from "@/features/controller/store";
import { startCase } from "@/util/str";
import {
  RemoveFileResponse,
  DeviceNode,
  DiscreteDevice,
  DeviceStepwise,
  CameraSettings,
  StepwiseDeviceProps,
  Device,
  MappedDevice,
} from "@/features/settings/interface";
import { props } from "@/util/obj";
import { isNumber } from "@/util/guards";
import { inRange } from "@/util/number";
import type { Nullable } from "@/util/ts-helpers";

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

export const extractDeviceAPI = (path?: Nullable<string>) => {
  if (!path) {
    return path;
  }

  const parts = path.split(":");
  if (parts.length > 1) {
    return parts.shift();
  }
};
export const extractDeviceId = (path?: Nullable<string>) => {
  if (!path) {
    return path;
  }

  const parts = path.split(":");
  if (parts.length > 1 && parts.shift()) {
    return parts.join(":");
  }
  return path;
};

const checkPixelFormat = (a?: Nullable<string>, b?: Nullable<string>) =>
  a === b || (!a && !b);

export const checkStepwiseFPS = (
  fps: Nullable<number>,
  stepwiseDevice: Pick<DeviceStepwise, "min_fps" | "max_fps">,
) =>
  isNumber(fps)
    ? inRange(fps, stepwiseDevice.min_fps, stepwiseDevice.max_fps)
    : true;

export const checkStepwiseSize = (
  deviceProps: Pick<CameraSettings, "width" | "height">,
  stepwiseDevice: DeviceStepwise,
) =>
  isNumber(deviceProps.width) &&
  isNumber(deviceProps.height) &&
  inRange(
    deviceProps.width,
    stepwiseDevice.min_width,
    stepwiseDevice.max_width,
  ) &&
  inRange(
    deviceProps.height,
    stepwiseDevice.min_height,
    stepwiseDevice.max_height,
  );

export const checkStepwiseProps = (
  deviceProps: Pick<
    CameraSettings,
    "pixel_format" | "fps" | "width" | "height"
  >,
  stepwiseDevice: DeviceStepwise,
) =>
  checkPixelFormat(deviceProps.pixel_format, stepwiseDevice.pixel_format) &&
  checkStepwiseSize(deviceProps, stepwiseDevice) &&
  checkStepwiseFPS(deviceProps.fps, stepwiseDevice);

export const checkNullableNumbers = (
  a: Nullable<number>,
  b: Nullable<number>,
) => (isNumber(a) && isNumber(b) ? a === b : false);

export const checkDiscreteProps = (
  deviceProps: Pick<
    CameraSettings,
    "pixel_format" | "fps" | "width" | "height"
  >,
  discreteProps: Pick<
    DiscreteDevice,
    "pixel_format" | "fps" | "width" | "height"
  >,
  scrictFPS = true,
) => {
  return checkPixelFormat(
    deviceProps.pixel_format,
    discreteProps.pixel_format,
  ) &&
    deviceProps.width === discreteProps.width &&
    deviceProps.height === discreteProps.height &&
    scrictFPS
    ? deviceProps.fps === discreteProps.fps
    : checkNullableNumbers(deviceProps.fps, discreteProps.fps);
};

export const checkDeviceProps = (
  item: Pick<CameraSettings, "pixel_format" | "fps" | "width" | "height">,
  device: Device,
  scrictFPS = true,
) => {
  if (isStepwiseDevice(device)) {
    return checkStepwiseProps(item, device);
  }
  return checkDiscreteProps(item, device, scrictFPS);
};

export const checkPath = (
  item: Pick<CameraSettings, "pixel_format" | "fps" | "width" | "height">,
  device: Device,
  scrictFPS = true,
) => {
  if (isStepwiseDevice(device)) {
    return checkStepwiseProps(item, device);
  }
  return checkDiscreteProps(item, device, scrictFPS);
};

export const findDevice = (
  item: Pick<
    CameraSettings,
    "device" | "pixel_format" | "fps" | "width" | "height"
  >,
  items: DeviceNode[],
) => {
  const stack = [...items];

  while (stack.length > 0) {
    const current = stack.pop();
    if (current) {
      if ((current as any).children) {
        stack.push(...(current as any).children);
      } else if (
        item.device === (current as any).device &&
        checkDeviceProps(item, current as unknown as MappedDevice)
      ) {
        return current as unknown as Device;
      }
    }
  }
};

export const findAlternative = (
  devicePath: string,
  data: Pick<CameraSettings, "pixel_format" | "fps" | "width" | "height">,
  devices: DeviceNode[],
  sameAPI?: boolean,
) => {
  const path = extractDeviceId(devicePath);
  const api = extractDeviceAPI(devicePath) || "v4l2";

  const alternatives: (Device & { score: number })[] = [];
  const stack = [...devices];

  while (stack.length > 0) {
    const current = stack.pop();
    if (current) {
      if ((current as any).children) {
        stack.push(...(current as any).children);
      } else if (
        (current as any).device &&
        path === extractDeviceId((current as any).device)
      ) {
        const devApi = extractDeviceAPI((current as any).device) || "v4l2";
        if (sameAPI) {
          if (api !== devApi) {
            continue;
          }
        } else {
          if (api === devApi) {
            continue;
          }
        }

        const device = current as unknown as MappedDevice;
        console.log(device.device, "DEVICE", device);
        const isStepwise = isStepwiseDevice(device);
        const pixelFormatMatch = checkPixelFormat(
          data.pixel_format,
          device.pixel_format,
        );

        const sizeMatch = isStepwise
          ? checkStepwiseSize(data, device)
          : data.width === device.width && data.height === device.height;

        const fpsMatch = isStepwise
          ? checkStepwiseFPS(data.fps, device)
          : !isNumber(data.fps) || data.fps === device.fps;

        const score = [
          sizeMatch ? 10 : -10,
          pixelFormatMatch ? 5 : -5,
          fpsMatch ? 1 : -1,
        ].reduce((acc, v) => acc + v, 0);

        alternatives.push({ ...device, score });
      }
    }
  }

  const sortedAlternatives = alternatives.sort(
    ({ score: a }, { score: b }) => b - a,
  );

  return sortedAlternatives[0];
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
      const step = stepWiseDevice[stepKey] || 1;
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

export const isStepwiseDevice = (data: any): data is DeviceStepwise =>
  data?.max_width;

export const generateLabel = (device: Device) => {
  if (isStepwiseDevice(device)) {
    const minSize = props(["min_width", "min_height"], device).join("x");
    const maxSize = props(["max_width", "max_height"], device).join("x");
    const fps = props(["min_fps", "max_fps"], device)
      .map((v) => `${v}`)
      .join("-")
      .concat("FPS");
    const size = `${minSize} - ${maxSize}`;
    return [device.pixel_format, size, fps, device.media_type]
      .filter((val) => !!val)
      .map((v) => `${v}`)
      .join(" ");
  }

  const size = props(["width", "height"], device).join("x");
  return [
    device.pixel_format,
    size,
    device.fps ? `${device.fps}FPS` : device.fps,
    device.media_type,
  ]
    .filter((val) => !!val)
    .map((v) => `${v}`)
    .join(" ");
};

export const groupDevices = (devices: Device[]): DeviceNode[] => {
  const deviceMap: { [key: string]: DeviceNode } = {};

  for (const device of devices) {
    const deviceKey = device.device;

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
