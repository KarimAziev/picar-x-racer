import type { FileDetail } from "@/features/files/interface";
import type { Props } from "@/features/files/components/Column.vue";

export type TableColumnsConfig<DataSource> = {
  [K in keyof Required<DataSource> as K]?: Omit<Props, "field"> & {
    class?: string;
  };
};

export const columnsConfig: TableColumnsConfig<FileDetail> = {
  name: {
    title: "Name",
    sortable: true,
  },
  size: {
    title: "Size",
    sortable: true,
  },
  modified: {
    title: "Date",
    sortable: true,
  },
  path: {
    title: "Actions",
  },
};

export const directoryChooserColumnsConfig: TableColumnsConfig<FileDetail> = {
  name: {
    title: "Name",
    sortable: true,
  },
  size: {
    title: "Size",
    sortable: true,
  },
  modified: {
    title: "Date",
    sortable: true,
  },
};
