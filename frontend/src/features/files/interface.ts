import { FilterMatchMode, SortDirection } from "@/features/files/enums";
import type { Nullable } from "@/util/ts-helpers";
import { ValueLabelOption } from "@/types/common";

export type APIMediaType = "image" | "music" | "data" | "video";

export interface FilterField {
  value: Nullable<string>;
  match_mode: FilterMatchMode;
}

export interface FilterBoolField {
  value: boolean;
  match_mode: FilterMatchMode;
}

export interface FilterFieldStringArray {
  value: Nullable<string[]>;
  match_mode: FilterMatchMode;
}

export interface FilterFieldDatetime {
  operator: Nullable<string>;
  constraints: [FilterField, FilterField];
  value: Nullable<string>;
}

export type Filter =
  | FilterFieldDatetime
  | FilterFieldStringArray
  | FilterBoolField
  | FilterField;

export interface SearchModel {
  value: string;
  field: string;
}

export interface OrderingModel {
  field?: string;
  direction: SortDirection;
}

export interface FileFilterModel {
  type: FilterFieldStringArray;
  file_suffixes: FilterFieldStringArray;
  modified: FilterFieldDatetime;
}

export interface FileDetail {
  name: string;
  path: string;
  size: number;
  is_dir: boolean;
  modified: Nullable<number>;
  type: string;
  content_type?: string;
  duration?: number;
}

export interface GroupedFile extends FileDetail {
  children?: GroupedFile[];
  children_count?: number;
}

export interface UploadingFileDetail extends GroupedFile {
  progress?: number;
}

export type FilterInfo = {
  [P in keyof FileFilterModel as FileFilterModel[P] extends FilterFieldStringArray
    ? P
    : never]: ValueLabelOption[];
};

export interface FileResponseModel {
  data: GroupedFile[];
  filter_info: FilterInfo;
  dir?: Nullable<string>;
  root_dir: string;
}

export interface FileFilterRequest {
  filters: FileFilterModel;
  search: SearchModel;
  ordering: OrderingModel;
}
export interface BatchFileStatus {
  success: boolean;
  filename: string;
  error: string | null;
}
