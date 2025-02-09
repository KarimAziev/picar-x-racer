import type { PresetOptionValue } from "@/features/settings/components/camera/config";
import { presetOptions } from "@/features/settings/components/camera/config";
import {
  CameraSettings,
  Device,
  DeviceNode,
  DeviceStepwise,
  MappedDevice,
  StepwiseDeviceProps,
} from "@/features/settings/interface";
import { isShallowEq, where } from "@/util/func";
import { isNumber } from "@/util/guards";
import { inRange } from "@/util/number";
import { props } from "@/util/obj";
import { Nullable } from "@/util/ts-helpers";

export type ItemData<Item> = {
  key: string;
  children?: ItemData<Item>[];
} & Item;

export const findStepwisePreset = ({
  width,
  height,
}: Partial<{
  [P in keyof PresetOptionValue]: Nullable<PresetOptionValue[P]>;
}>) =>
  presetOptions.find((item) =>
    where({ width: isShallowEq(width), height: isShallowEq(height) })(
      item.value,
    ),
  );

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

export const findAlternative = (
  devicePath: string,
  data: Pick<CameraSettings, "pixel_format" | "fps" | "width" | "height">,
  devices: (DeviceNode | MappedDevice)[],
  sameAPI?: boolean,
) => {
  const path = extractDeviceId(devicePath);
  const api = extractDeviceAPI(devicePath) || "v4l2";

  let bestAlternative: (Device & { score: number }) | null = null;
  const stack = [...devices];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }

    if ((current as any).children) {
      stack.push(...(current as any).children);
      continue;
    }

    if (
      (current as any).device &&
      path === extractDeviceId((current as any).device)
    ) {
      const devApi = extractDeviceAPI((current as any).device) || "v4l2";
      if (sameAPI && api !== devApi) {
        continue;
      } else if (!sameAPI && api === devApi) {
        continue;
      }

      const device = current as unknown as MappedDevice;
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

      const score =
        (sizeMatch ? 10 : -10) +
        (pixelFormatMatch ? 10 : -10) +
        (fpsMatch ? 1 : -1);

      if (bestAlternative === null || score > bestAlternative.score) {
        bestAlternative = { ...device, score };
      }
    }
  }

  return bestAlternative;
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

const flattenNode = (
  node: DeviceNode | MappedDevice,
  isRoot: boolean = false,
) => {
  if (
    "children" in node &&
    Array.isArray(node.children) &&
    node.children.length
  ) {
    node.children = node.children.map((child) => flattenNode(child));

    if (!isRoot && node.children.length === 1) {
      return node.children[0];
    }
  }
  return node;
};

export const groupDevices = (devices: Device[]) => {
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

  return Object.values(deviceMap).map((node) => flattenNode(node, true));
};
