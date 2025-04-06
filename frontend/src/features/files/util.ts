import { isString } from "@/util/guards";
import type {
  BatchFileStatus,
  FilterFieldStringArray,
} from "@/features/files/interface";
import { Nullable } from "@/util/ts-helpers";
import { allPass } from "@/util/func";

export function bytesToSize(bytes: number, decimals = 1) {
  const sizes = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "YB"];
  const i = bytes === 0 ? 0 : Math.floor(Math.log(bytes) / Math.log(1000));

  const result = !sizes[i]
    ? null
    : i === 0
      ? `${bytes} ${sizes[i]}`
      : `${(bytes / 1000 ** i).toFixed(decimals)} ${sizes[i]}`;

  return result;
}

export const getBatchFilesErrorMessage = (
  data: BatchFileStatus[],
  operation: string,
) => {
  const { success, failed } = data.reduce(
    (acc, obj) => {
      const prop = obj.success ? "success" : "failed";
      acc[prop].push(obj);
      return acc;
    },
    {
      success: [] as BatchFileStatus[],
      failed: [] as BatchFileStatus[],
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

export const extractContentDispositionFilename = (
  contentDisposition?: string,
) => {
  if (!isString(contentDisposition)) {
    return;
  }
  const filenameMatch = contentDisposition.match(
    /filename\*?=["']?(?:UTF-8'')?([^;"']+)["']?/,
  );
  if (filenameMatch && filenameMatch[1]) {
    return decodeURIComponent(filenameMatch[1]);
  }
};

export type ItemData<Item> = {
  key: string;
  children?: ItemData<Item>[];
} & Item;

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

export const isPlainFilter = (filter: any): filter is FilterFieldStringArray =>
  filter && Object.hasOwn(filter, "match_mode") && filter.match_mode;

export const mapConcat = (vals: Nullable<string>[], separator = "") =>
  vals.filter((v) => v).join(separator);

export const expandFileName = (
  file: string,
  ...dirs: (string | null | undefined)[]
) => {
  const filteredDirs = dirs.filter(allPass([isString, (v) => v.length > 0]));
  return [...filteredDirs, file].join("/");
};
