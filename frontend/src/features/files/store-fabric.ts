import axios from "axios";
import { defineStore } from "pinia";
import { useMessagerStore } from "@/features/messager";
import {
  downloadFile,
  removeFile,
  batchRemoveFiles,
  downloadFilesAsArchive,
  batchMoveFiles,
  renameFile,
  makeDir,
} from "@/features/files/api";
import type {
  FileResponseModel,
  GroupedFile,
  APIMediaType,
  FileFilterRequest,
  UploadingFileDetail,
  FileFilterModel,
  FilterInfo,
} from "@/features/files/interface";
import { getBatchFilesErrorMessage } from "@/features/settings/util";
import { SortDirection } from "@/features/files/enums";
import type { Nullable } from "@/util/ts-helpers";
import { omit, cloneDeep } from "@/util/obj";
import { FilterMatchMode } from "@/features/files/enums";
import { isArray, isEmpty } from "@/util/guards";
import { where, allPass } from "@/util/func";

export interface State {
  data: GroupedFile[];
  uploadingData: Record<string, UploadingFileDetail>;
  loading: boolean;
  emptyMessage?: string;
  filter_info: FilterInfo;
  filters: FileFilterModel;
  search: FileFilterRequest["search"];
  ordering: FileFilterRequest["ordering"];
  removingRows: Record<string, boolean>;
  downloadingRows: Record<string, boolean>;
  dir?: Nullable<string>;
  root_dir?: string;
}

const defaultState: State = {
  loading: false,
  emptyMessage: "No data",
  data: [],
  ordering: {
    field: "modified",
    direction: SortDirection.DESC,
  },

  filters: {
    type: {
      value: null,
      match_mode: FilterMatchMode.IN,
    },
    file_suffixes: {
      value: null,
      match_mode: FilterMatchMode.IN,
    },
  },
  filter_info: {
    type: [],
    file_suffixes: [],
  },
  search: {
    value: "",
    field: "name",
  },
  removingRows: {},
  downloadingRows: {},
  uploadingData: {},
};

export const makeFileStore = (
  scope: APIMediaType,
  initialState?: Partial<
    Pick<State, "filters" | "filter_info" | "ordering" | "search">
  >,
  name?: string,
) =>
  defineStore(name || scope, {
    state: () => ({ ...cloneDeep(defaultState), ...cloneDeep(initialState) }),
    getters: {
      mediaType() {
        return scope;
      },
      hasFilters({ filters }) {
        return Object.values(filters).some((item) =>
          where({ value: allPass([isArray, (v) => !isEmpty(v)]) }, item),
        );
      },
    },

    actions: {
      async fetchData() {
        const messager = useMessagerStore();
        try {
          this.loading = true;
          this.emptyMessage = defaultState["emptyMessage"];
          const response = await axios.post<FileResponseModel>(
            `/api/files/list/${scope}`,
            {
              dir: this.dir,
              search: this.search,
              filters: this.filters,
              ordering: this.ordering,
            },
          );
          this.filter_info = response.data.filter_info;
          this.data = response.data.data;
          this.dir = response.data.dir;
          this.root_dir = response.data.root_dir;
        } catch (error) {
          messager.handleError(error, "Error fetching data");
          this.emptyMessage = "Failed to fetch data";
        } finally {
          this.loading = false;
        }
      },

      async removeFile(fileName: string) {
        const messager = useMessagerStore();
        try {
          this.removingRows[fileName] = true;
          await removeFile(scope, fileName);
        } catch (error) {
          messager.handleError(error);
        } finally {
          delete this.removingRows[fileName];
        }
      },
      async batchRemoveFiles(filenames: string[]) {
        const messager = useMessagerStore();

        try {
          this.loading = true;
          const removingHash = filenames.reduce(
            (acc, key) => {
              acc[key] = true;
              return acc;
            },
            { ...this.removingRows },
          );
          this.removingRows = removingHash;
          const { data } = await batchRemoveFiles(scope, filenames);
          const msgParams = getBatchFilesErrorMessage(data, "remove");
          if (msgParams) {
            messager.error(msgParams.error, msgParams.title);
          }
        } catch (error) {
          messager.handleError(error);
        } finally {
          this.removingRows = omit(filenames, this.removingRows);
          this.loading = false;
        }
      },
      async renameFile(fileName: string, newName: string) {
        const messager = useMessagerStore();
        try {
          this.downloadingRows[fileName] = true;

          await renameFile(
            scope,
            fileName,
            this.dir ? `${this.dir}/${newName}` : newName,
          );
        } catch (error) {
          messager.handleError(error);
        } finally {
          delete this.downloadingRows[fileName];
        }
      },
      async makeDir(fileName: string) {
        const messager = useMessagerStore();

        try {
          this.loading = true;
          this.downloadingRows[fileName] = true;

          await makeDir(scope, this.dir ? `${this.dir}/${fileName}` : fileName);
        } catch (error) {
          messager.handleError(error);
        } finally {
          delete this.downloadingRows[fileName];
          this.loading = false;
        }
      },
      async batchMoveFiles(filenames: string[], dir: string) {
        const messager = useMessagerStore();

        try {
          this.loading = true;
          const removingHash = filenames.reduce(
            (acc, key) => {
              acc[key] = true;
              return acc;
            },
            { ...this.removingRows },
          );
          this.removingRows = removingHash;
          const { data } = await batchMoveFiles(scope, filenames, dir);
          const msgParams = getBatchFilesErrorMessage(data, "move");
          if (msgParams) {
            messager.error(msgParams.error, msgParams.title);
          }
        } catch (error) {
          messager.handleError(error);
        } finally {
          this.removingRows = omit(filenames, this.removingRows);
          this.loading = false;
        }
      },
      async downloadFile(fileName: string) {
        const messager = useMessagerStore();
        const progressFn = messager.makeProgress("Downloading");
        try {
          this.downloadingRows[fileName] = true;
          await downloadFile(scope, fileName, progressFn);
        } catch (error) {
          messager.handleError(error);
        } finally {
          delete this.downloadingRows[fileName];
        }
      },
      async downloadFilesArchive(filenames: string[]) {
        const messager = useMessagerStore();
        const progressFn = messager.makeProgress("Downloading archive");
        try {
          this.downloadingRows = filenames.reduce(
            (acc, key) => {
              acc[key] = true;
              return acc;
            },
            { ...this.removingRows },
          );
          await downloadFilesAsArchive(scope, filenames, progressFn);
        } catch (error) {
          messager.handleError(error);
        } finally {
          this.downloadingRows = omit(filenames, this.removingRows);
        }
      },
      async resetFilters() {
        Object.keys(this.filters).forEach((key) => {
          this.filters[key as keyof typeof this.filters].value = null;
        });
        await this.fetchData();
      },
    },
  });

export type FileStore = ReturnType<ReturnType<typeof makeFileStore>>;
