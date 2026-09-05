import { defineStore } from "pinia";
import { robotApi } from "@/api";
import { retrieveError } from "@/util/error";

export interface AuxiliarySensorReading {
  name: string;
  driver: string;
  kind: "environmental" | "magnetometer";
  timestamp_monotonic_ns: number | null;
  temperature_c: number | null;
  relative_humidity_percent: number | null;
  pressure_pa: number | null;
  magnetic_field_t: [number, number, number] | null;
  error: string | null;
}

interface State {
  readings: AuxiliarySensorReading[];
  loading: boolean;
  error: string | null;
}

export const useAuxiliarySensorStore = defineStore("auxiliary-sensors", {
  state: (): State => ({
    readings: [],
    loading: false,
    error: null,
  }),
  actions: {
    setReadings(payload: AuxiliarySensorReading[]) {
      this.readings = payload;
      this.loading = false;
      this.error = null;
    },
    async fetchReadings() {
      try {
        this.loading = true;
        const readings = await robotApi.get<AuxiliarySensorReading[]>(
          "/px/api/auxiliary-sensors",
        );
        this.setReadings(readings);
      } catch (error) {
        this.error = retrieveError(error).text;
      } finally {
        this.loading = false;
      }
    },
  },
});
