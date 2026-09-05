// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import {
  useAuxiliarySensorStore,
  type AuxiliarySensorReading,
} from "./store";

const reading = (
  name: string,
  temperature: number,
): AuxiliarySensorReading => ({
  name,
  driver: "mock_environmental",
  kind: "environmental",
  timestamp_monotonic_ns: 1,
  temperature_c: temperature,
  relative_humidity_percent: 45,
  pressure_pa: 101_325,
  magnetic_field_t: null,
  error: null,
});

describe("auxiliary sensor store", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("replaces the complete named sensor snapshot", () => {
    const store = useAuxiliarySensorStore();
    store.setReadings([reading("Cabin", 20), reading("Barometer", 21)]);
    store.setReadings([reading("Cabin", 22)]);

    expect(store.readings).toEqual([reading("Cabin", 22)]);
  });
});
