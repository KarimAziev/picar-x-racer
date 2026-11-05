import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { useStore as useSettingsStore } from "@/features/settings/stores/settings";
import { appApi } from "@/api";
import { retrieveError } from "@/util/error";

export interface PmicReading {
  name: string;
  value: number;
  unit: "V" | "A";
}

export interface PmicStatus {
  readings: PmicReading[];
  measured_at: string | null;
  error: string | null;
}

export const usePmicStore = defineStore("pmic", () => {
  const settingsStore = useSettingsStore();
  const selectedChannels = computed({
    get: () => settingsStore.data.pmic.selected_channels,
    set: (value: string[]) => {
      settingsStore.data.pmic.selected_channels = value;
    },
  });
  const refreshSeconds = computed({
    get: () => settingsStore.data.pmic.refresh_seconds,
    set: (value: number) => {
      settingsStore.data.pmic.refresh_seconds = value;
    },
  });
  const enabled = computed({
    get: () => settingsStore.data.pmic.enabled,
    set: (value: boolean) => {
      settingsStore.data.pmic.enabled = value;
    },
  });
  const readings = ref<PmicReading[]>([]);
  const measuredAt = ref<string | null>(null);
  const error = ref<string | null>(null);
  const loading = ref(false);
  const intervalMs = computed(
    () =>
      (Number.isFinite(refreshSeconds.value)
        ? Math.min(300, Math.max(1, refreshSeconds.value))
        : 5) * 1000,
  );
  const channels = computed(() =>
    Array.isArray(selectedChannels.value)
      ? selectedChannels.value.filter((name) => typeof name === "string")
      : ["3V3_SYS_V", "3V3_SYS_A"],
  );
  const selectedReadings = computed(() =>
    channels.value.map((name) => ({
      name,
      reading: readings.value.find((reading) => reading.name === name),
    })),
  );
  let timer: ReturnType<typeof setTimeout> | undefined;
  let polling = false;
  let generation = 0;
  let controller: AbortController | undefined;

  async function refresh() {
    if (loading.value) return;
    const requestGeneration = generation;
    controller = new AbortController();
    loading.value = true;
    try {
      const result = await appApi.get<PmicStatus>("/api/system/pmic", {
        signal: controller.signal,
      });
      if (requestGeneration !== generation) return;
      readings.value = result.readings;
      measuredAt.value = result.measured_at;
      error.value = result.error;
    } catch (cause) {
      if (requestGeneration !== generation) return;
      readings.value = [];
      measuredAt.value = null;
      error.value = retrieveError(cause).text;
    } finally {
      if (requestGeneration === generation) {
        loading.value = false;
        controller = undefined;
      }
    }
  }

  async function poll(currentGeneration: number) {
    await refresh();
    if (polling && currentGeneration === generation) {
      timer = setTimeout(() => void poll(currentGeneration), intervalMs.value);
    }
  }

  function stopPolling() {
    polling = false;
    generation++;
    clearTimeout(timer);
    controller?.abort();
    controller = undefined;
    loading.value = false;
  }

  function startPolling() {
    stopPolling();
    polling = true;
    void poll(generation);
  }

  async function savePreferences() {
    await settingsStore.saveData({
      pmic: {
        enabled: enabled.value,
        selected_channels: [...channels.value],
        refresh_seconds: Math.round(intervalMs.value / 1000),
      },
    });
  }

  return {
    selectedChannels,
    refreshSeconds,
    enabled,
    readings,
    measuredAt,
    error,
    loading,
    intervalMs,
    channels,
    selectedReadings,
    refresh,
    startPolling,
    stopPolling,
    savePreferences,
  };
});
