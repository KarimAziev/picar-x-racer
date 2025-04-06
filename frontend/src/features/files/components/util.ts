import { ValueLabelOption } from "@/types/common";
import type {
  UploadingFileDetail,
  GroupedFile,
} from "@/features/files/interface";
import { Nullable } from "@/util/ts-helpers";

export type ItemData<Item> = {
  children?: ItemData<Item>[];
  [key: string]: any;
} & Item;

export const addTabIndexes = <DataItem>(
  keyProp: keyof DataItem,
  items: ItemData<DataItem>[],
  expandedNodes: Set<string>,
  counter = { value: 1 },
): DataItem[] => {
  return items.map((item) => {
    const tabIdx = counter.value++;
    const itemKey = item[keyProp];
    if (item.children && expandedNodes.has(itemKey)) {
      return {
        ...item,
        tabIdx,
        children: addTabIndexes(keyProp, item.children, expandedNodes, counter),
      };
    }

    return {
      ...item,
      tabIdx,
    };
  });
};

export const flattenExpandedTree = <DataItem>(
  keyProp: keyof DataItem,
  items: ItemData<DataItem>[],
  expandedNodes: Set<string>,
): DataItem[] => {
  const result: DataItem[] = [];

  for (const item of items) {
    result.push(item);

    if (item.children && expandedNodes.has(item[keyProp])) {
      result.push(
        ...flattenExpandedTree(keyProp, item.children, expandedNodes),
      );
    }
  }

  return result;
};

export const findItemInTree = <DataItem>(
  keyProp: keyof DataItem,
  value: any,
  items: ItemData<DataItem>[],
): DataItem | undefined => {
  for (const item of items) {
    if (item[keyProp] === value) {
      return item;
    }

    if (item.children) {
      const found = findItemInTree(keyProp, value, item.children);
      if (found !== undefined) {
        return found;
      }
    }
  }
  return undefined;
};
export const isVideoType = (str?: string) => str === "video";
export const isImageType = (str?: string) => str === "image";
export const isMusicType = (str?: string) => str === "audio";
export const isDirectoryType = (str?: string) => str === "directory";
export const isTextFile = (str?: string) => str === "text";
export const isLoadable = (str?: string) => str === "loadable";

export const getExpandableIds = <DataItem>(
  keyProp: keyof DataItem,
  items: ItemData<DataItem>[],
) => {
  const result = new Set<string>();

  const stack = [...items];

  while (stack.length > 0) {
    const current = stack.pop();

    if (!current) {
      continue;
    }

    if (current.children) {
      result.add(current[keyProp]);
      stack.push(...current.children);
      continue;
    }
  }

  return result;
};

export const toBreadcrumbs = (path: string): ValueLabelOption[] => {
  const segments = path.split("/");

  return segments.flatMap((segment, index) => {
    const value = segments.slice(0, index + 1).join("/");

    return value.length > 0 ? [{ label: segment, value }] : [];
  });
};

export const uploadingFileToRow = (
  file: File,
  progress: number,
  dir?: Nullable<string>,
): UploadingFileDetail => ({
  name: file.name,
  path: [dir, file.name].filter((v) => !!v).join("/"),
  type: "",
  is_dir: false,
  size: file.size,
  modified: Math.floor(file.lastModified / 1000),
  progress,
});

export const getParent = (path: string): string => {
  const i = path.lastIndexOf("/");
  return i > -1 ? path.substring(0, i) : "";
};

export const mergeRows = (
  base: GroupedFile[],
  parentPath: string,
  uploadingData: Record<string, UploadingFileDetail>,
): GroupedFile[] => {
  const basePaths = new Set(base.map((item) => item.path));

  const baseDirs = base.filter((item) => !!item.children);
  const baseFiles = base.filter((item) => !item.children);

  const mergedDirs = baseDirs.map((dir) => {
    return {
      ...dir,
      children: mergeRows(dir.children || [], dir.path, uploadingData),
    };
  });

  const uploadingAtLevel = Object.values(uploadingData).filter(
    (file: GroupedFile | UploadingFileDetail) =>
      getParent(file.path) === parentPath,
  );

  return [
    ...mergedDirs,
    ...uploadingAtLevel.filter((file) => !basePaths.has(file.path)),
    ...baseFiles,
  ];
};

export const formatModifiedTimeToDate = (modified: number) =>
  new Date(modified * 1000);

export const formatModifiedTime = (modified: number) =>
  formatModifiedTimeToDate(modified).toLocaleDateString();
