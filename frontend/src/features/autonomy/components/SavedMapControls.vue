<template>
  <details
    class="mt-3 border-t border-surface-200 pt-3 dark:border-surface-700"
  >
    <summary class="cursor-pointer py-2 text-sm font-semibold">
      Saved maps
    </summary>
    <p class="mb-3 text-xs text-surface-500">
      Finish freezes the current map in memory. Save keeps a copy across backend
      restarts.
    </p>
    <p
      v-if="store.savedMapError"
      role="alert"
      class="mb-3 text-xs text-red-600 dark:text-red-300"
    >
      {{ store.savedMapError }}
    </p>
    <p
      v-if="store.savedMapMessage"
      role="status"
      class="mb-3 text-xs text-green-700 dark:text-green-300"
    >
      {{ store.savedMapMessage }}
    </p>
    <form class="flex flex-col gap-2" @submit.prevent="store.saveMap(name)">
      <label for="saved-map-name" class="text-xs">Map name</label>
      <input
        id="saved-map-name"
        v-model="name"
        class="map-input"
        maxlength="80"
        placeholder="Flat — September scan"
      />
      <Button
        type="submit"
        label="Save current map"
        icon="pi pi-save"
        size="small"
        :disabled="!canSave"
        :loading="store.savedMapBusy"
      />
    </form>
    <div class="mt-4 flex items-center justify-between gap-2">
      <label for="saved-map-selection" class="text-xs">Load a saved map</label>
      <Button
        label="Refresh"
        icon="pi pi-refresh"
        severity="secondary"
        text
        size="small"
        :disabled="store.savedMapBusy"
        :loading="store.savedMapsLoading"
        @click="store.refreshSavedMaps()"
      />
    </div>
    <select
      id="saved-map-selection"
      v-model="selectedId"
      class="map-input w-full"
    >
      <option value="">Select a saved map…</option>
      <option v-for="item in store.savedMaps" :key="item.id" :value="item.id">
        {{ item.name }} · {{ new Date(item.created_at).toLocaleString() }}
      </option>
    </select>
    <p
      v-if="!store.savedMaps.length && !store.savedMapsLoading"
      class="mt-2 text-xs text-surface-500"
    >
      No saved maps listed. Save a finished scan first, or refresh the list.
    </p>
    <form
      v-if="selectedId"
      class="mt-3 flex flex-col gap-2"
      @submit.prevent="load"
    >
      <p class="text-xs text-surface-500">
        Enter the robot's current rear-axle position and heading in the saved
        map's coordinates. This is a manual alignment, not automatic
        relocalization.
      </p>
      <p v-if="selected?.saved_pose" class="text-xs">
        At save time: X {{ selected.saved_pose.x_m.toFixed(2) }} m, Y
        {{ selected.saved_pose.y_m.toFixed(2) }} m, heading
        {{ selected.saved_pose.yaw_deg.toFixed(1) }}°. Only reuse these values
        if the robot is back at that placement.
      </p>
      <label for="saved-map-x" class="text-xs">Robot X in saved map (m)</label>
      <input
        id="saved-map-x"
        v-model="x"
        type="number"
        step="any"
        class="map-input"
        required
      />
      <label for="saved-map-y" class="text-xs">Robot Y in saved map (m)</label>
      <input
        id="saved-map-y"
        v-model="y"
        type="number"
        step="any"
        class="map-input"
        required
      />
      <label for="saved-map-yaw" class="text-xs"
        >Heading (degrees, −180 to 180)</label
      >
      <input
        id="saved-map-yaw"
        v-model="yaw"
        type="number"
        step="any"
        min="-180"
        max="180"
        class="map-input"
        required
      />
      <label class="flex items-start gap-2 py-2 text-xs">
        <input v-model="confirmed" type="checkbox" class="map-confirmation" />
        I checked the robot's placement. Replace the current in-memory map with
        this saved map.
      </label>
      <p class="text-xs text-surface-500">
        Disarm and pause/finish mapping first. Loading never starts motion.
        Loaded maps are frozen references; clear the map before making a new
        scan.
      </p>
      <Button
        type="submit"
        label="Load at this placement"
        icon="pi pi-folder-open"
        severity="secondary"
        size="small"
        :disabled="!canLoad"
        :loading="store.savedMapBusy"
      />
    </form>
  </details>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useAutonomyStore } from "@/features/autonomy/store";
import { useControllerStore } from "@/features/controller/store";

const store = useAutonomyStore();
const controller = useControllerStore();
const name = ref("");
const selectedId = ref("");
const x = ref<number | string>("");
const y = ref<number | string>("");
const yaw = ref<number | string>("");
const confirmed = ref(false);
const selected = computed(() =>
  store.savedMaps.find((item) => item.id === selectedId.value),
);
const inactive = computed(
  () =>
    Boolean(store.mappingSession?.enabled) &&
    store.mappingSession?.state !== "active",
);
const busy = computed(
  () =>
    store.savedMapBusy || store.savedMapsLoading || store.mappingActionLoading,
);
const canSave = computed(
  () =>
    inactive.value &&
    store.mappingSession?.has_map &&
    name.value.trim().length > 0 &&
    !busy.value,
);
const canLoad = computed(
  () =>
    inactive.value &&
    !busy.value &&
    controller.robotMode === "disarmed" &&
    ![
      store.navigationExecution?.state,
      store.navigationMissionExecution?.state,
    ].some((state) => state === "running" || state === "paused") &&
    confirmed.value &&
    selected.value &&
    [x.value, y.value, yaw.value].every(
      (value) => value !== "" && Number.isFinite(Number(value)),
    ) &&
    Math.abs(Number(yaw.value)) <= 180,
);

watch([selectedId, x, y, yaw], () => {
  confirmed.value = false;
});
const load = async () => {
  if (!canLoad.value) return;
  if (
    await store.loadSavedMap(selectedId.value, {
      x_m: Number(x.value),
      y_m: Number(y.value),
      yaw_deg: Number(yaw.value),
    })
  ) {
    confirmed.value = false;
  }
};
onMounted(() => void store.refreshSavedMaps());
</script>

<style scoped>
.map-input {
  width: 100%;
  min-height: 2.75rem;
  min-width: 0;
  border: 1px solid var(--p-surface-400);
  border-radius: 0.375rem;
  background: transparent;
  padding: 0.5rem;
  font-size: 0.75rem;
}
.map-confirmation {
  width: 1.25rem;
  height: 1.25rem;
  min-width: 1.25rem;
  margin: 0;
  padding: 0;
}
</style>
