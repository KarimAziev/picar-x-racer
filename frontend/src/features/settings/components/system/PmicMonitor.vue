<template>
  <Button
    variant="text"
    size="small"
    class="max-w-[32vw]"
    aria-label="PMIC power monitor settings"
    :title="`PMIC power monitor: ${summary}`"
    @click="popover?.toggle($event)"
  >
    <i class="pi pi-bolt shrink-0" aria-hidden="true" />
    <span class="truncate text-xs tabular-nums">{{ summary }}</span>
  </Button>
  <Popover ref="popover">
    <section
      class="flex w-80 max-w-[80vw] flex-col gap-3"
      aria-label="PMIC power monitor"
    >
      <div class="flex items-center justify-between gap-2">
        <span class="font-semibold">Pi power rails</span>
        <ToggleSwitch
          v-model="store.enabled"
          aria-label="Enable PMIC monitoring"
        />
      </div>
      <p class="m-0 text-xs text-surface-500 dark:text-surface-400">
        Rail readings include board loads and connected peripherals. USB and
        direct 5 V loads are not included in current measurements.
      </p>
      <label for="pmic-channels" class="text-sm">Displayed channels</label>
      <MultiSelect
        input-id="pmic-channels"
        v-model="store.selectedChannels"
        :options="channelOptions"
        option-label="label"
        option-value="name"
        placeholder="Select channels"
        filter
        :max-selected-labels="1"
        selected-items-label="{0} channels selected"
      />
      <div class="flex items-center justify-between gap-3">
        <label for="pmic-interval" class="text-sm"
          >Refresh interval (seconds)</label
        >
        <InputNumber
          input-id="pmic-interval"
          :model-value="store.intervalMs / 1000"
          @update:model-value="store.refreshSeconds = $event ?? 5"
          :min="1"
          :max="300"
          :max-fraction-digits="0"
          show-buttons
          input-class="w-16"
        />
      </div>
      <p v-if="!store.enabled" class="m-0 text-sm">Monitoring paused.</p>
      <p
        v-else-if="store.error"
        role="status"
        class="m-0 text-sm text-amber-600 dark:text-amber-400"
      >
        {{ store.error }}
      </p>
      <dl v-else class="m-0 max-h-60 overflow-y-auto text-sm">
        <div
          v-for="item in store.selectedReadings"
          :key="item.name"
          class="flex justify-between gap-4 py-1"
        >
          <dt>{{ channelLabel(item.name) }}</dt>
          <dd class="m-0 font-mono tabular-nums">
            {{ formatReading(item.reading) }}
          </dd>
        </div>
      </dl>
      <p v-if="!store.channels.length" class="m-0 text-xs">
        Select a channel to display its reading.
      </p>
      <div
        class="flex items-center justify-between gap-2 text-xs text-surface-500 dark:text-surface-400"
      >
        <span>{{ updatedLabel }}</span>
        <Button
          label="Refresh"
          icon="pi pi-refresh"
          variant="text"
          size="small"
          :loading="store.loading"
          :disabled="!store.enabled"
          @click="store.refresh()"
        />
      </div>
      <Button
        label="Save settings"
        icon="pi pi-save"
        size="small"
        outlined
        :loading="settingsStore.saving"
        @click="store.savePreferences()"
      />
    </section>
  </Popover>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { useDocumentVisibility } from "@vueuse/core";
import Button from "primevue/button";
import Popover from "primevue/popover";
import MultiSelect from "primevue/multiselect";
import InputNumber from "primevue/inputnumber";
import ToggleSwitch from "primevue/toggleswitch";
import {
  usePmicStore,
  type PmicReading,
} from "@/features/settings/stores/pmic";

import { useStore as useSettingsStore } from "@/features/settings/stores/settings";

const store = usePmicStore();
const settingsStore = useSettingsStore();
const popover = ref<InstanceType<typeof Popover>>();
const visibility = useDocumentVisibility();
const channelLabel = (name: string) =>
  `${name.replace(/_[AV]$/, "").replaceAll("_", " ")} · ${name.endsWith("_A") ? "current" : "voltage"}`;
const formatReading = (reading?: PmicReading) =>
  reading ? `${reading.value.toFixed(3)} ${reading.unit}` : "Unavailable";
const channelOptions = computed(() =>
  [
    ...new Set([
      ...store.channels,
      ...store.readings.map((reading) => reading.name),
    ]),
  ]
    .sort()
    .map((name) => ({ name, label: channelLabel(name) })),
);
const summary = computed(() => {
  if (!store.enabled) return "PMIC paused";
  if (store.error) return "PMIC unavailable";
  if (!store.measuredAt) return "PMIC…";
  const first = store.selectedReadings[0];
  if (!first) return "PMIC";
  const rail = first.name.replace(/_[AV]$/, "");
  const pair = store.selectedReadings.find(
    (item) =>
      item.name !== first.name && item.name.replace(/_[AV]$/, "") === rail,
  );
  const remaining = store.selectedReadings.length - (pair ? 2 : 1);
  return `${rail.replaceAll("_", " ")} ${formatReading(first.reading)}${pair ? ` · ${formatReading(pair.reading)}` : ""}${remaining > 0 ? ` +${remaining}` : ""}`;
});
const updatedLabel = computed(() =>
  store.measuredAt
    ? `Measured ${new Date(store.measuredAt).toLocaleTimeString()}`
    : "No measurement",
);

watch(
  () => [store.enabled, store.intervalMs, visibility.value],
  () => {
    if (store.enabled && visibility.value === "visible") store.startPolling();
    else store.stopPolling();
  },
  { immediate: true },
);
onUnmounted(store.stopPolling);
</script>
