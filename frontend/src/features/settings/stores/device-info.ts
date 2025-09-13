import { defineStore } from "pinia";
import { useMessagerStore } from "@/features/messager";
import { robotApi } from "@/api";
import { normalizePins } from "@/ui/PinChooser/util";
import type { ValueLabelOption } from "@/types/common";

export interface PinInfo {
  /**
   * Pin name to display
   */
  name: string;
  /**
   * An integer containing the physical pin number on the header (starting from 1 in accordance with convention).
   */
  number: number;
  /**
   * An integer indicating on which row the pin is physically located in the header (1-based)
   *
   */
  /**
   * GPIO number if any
   */
  gpio_number: number | null;

  /**
   * An integer indicating on which row the pin is physically located in the header (1-based)
   */
  row: number;
  /**
   * An integer indicating in which column the pin is physically located in the header (1-based)
   */
  col: number;
  /**
   * All the string-names that can be used to identify this pin
   */
  names: string[];

  /**
   * Mapping interfaces that the pin can be a part of.
   */
  interfaces: string[];
}

export interface PinHeader {
  name: string;
  /**
   * The number of columns on the header.
   */
  columns: number;
  /**
   * The number of rows on the header.
   */
  rows: number;
  pins: {
    [key: string]: PinInfo;
  };
}

export type PinMapping = {
  [key: string]: PinHeader;
};

export interface PinInfoNormalized extends PinInfo {
  selectable?: boolean;
  layouts: Record<string, string>;
}

export interface LayoutOption extends ValueLabelOption {
  count: number;
}

export interface BoardInfo {
  model: string;
  bluetooth: boolean;
  csi: number;
  dsi: number;
  eth_speed: number;
  ethernet: number;
  manufacturer: string;
  memory: number;
  pcb_revision: string;
  released: string;
  revision: string;
  soc: string;
  storage: string;
  usb: number;
  usb3: number;
  wifi: boolean;
}
export interface DeviceInfo {
  board: BoardInfo;
  headers: PinMapping;
}

export interface State {
  pins: PinMapping;
  board: BoardInfo | null;
  loading: boolean;
  loaded?: boolean;
  hash: Map<string | number, PinInfoNormalized>;
  layoutOptions: LayoutOption[];
}

const defaultState: State = {
  loading: false,
  loaded: false,
  pins: {},
  hash: new Map(),
  board: null,
  layoutOptions: [],
};

export const useStore = defineStore("device-info", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        const response = await robotApi.get<DeviceInfo>(
          "/px/api/settings/pins",
        );

        const headers = response.headers;

        const { hash, layoutOptions } = normalizePins(headers);

        this.pins = headers;
        this.board = response.board;
        this.hash = hash;
        this.layoutOptions = layoutOptions;
        this.loaded = true;
      } catch (error) {
        messager.handleError(error);
      } finally {
        this.loading = false;
      }
    },
    async fetchDataOnce() {
      if (this.loaded || this.loading) {
        return;
      }
      this.loading = true;
      return await this.fetchData();
    },
  },
});
