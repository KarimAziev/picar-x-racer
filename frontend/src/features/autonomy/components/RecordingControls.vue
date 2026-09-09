<template>
  <section class="rounded-xl border border-surface-200 bg-surface-0 p-3 shadow-sm dark:border-surface-700 dark:bg-surface-900">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-semibold">Session recording</h2>
      <Tag :severity="store.recording?.active ? 'danger' : 'secondary'"
        :value="store.recording?.active ? 'Recording' : 'Stopped'" />
    </div>
    <p class="mt-1 text-xs text-surface-500">
      Capture sensors, motion commands, and mission events for offline diagnosis.
      Recording does not move the vehicle.
    </p>
    <p v-if="store.recordingError || store.recordingStatusError || store.recording?.error" role="alert"
      class="mt-2 text-xs text-red-600 dark:text-red-300">
      {{ store.recordingError || store.recordingStatusError || store.recording?.error }}
    </p>
    <p v-if="store.recording?.dropped_events" role="alert"
      class="mt-2 text-xs text-amber-600 dark:text-amber-300">
      {{ store.recording.dropped_events }} events dropped. This recording has gaps.
    </p>
    <p v-if="store.recording?.session_id" class="mt-2 text-xs text-surface-500">
      {{ store.recording.events_written.toLocaleString() }} events ·
      {{ (store.recording.bytes_written / 1048576).toFixed(1) }} MB
    </p>
    <div class="mt-3 flex items-center gap-3">
      <Button :label="store.recording?.active ? 'Stop recording' : 'Start recording'"
        :icon="store.recording?.active ? 'pi pi-stop' : 'pi pi-circle'"
        size="small" :loading="store.recordingLoading"
        @click="store.runRecordingAction(store.recording?.active ? 'stop' : 'start')" />
      <a v-if="downloadUrl" :href="downloadUrl" download class="text-xs text-blue-600 underline dark:text-blue-300">
        Download session
      </a>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from "vue";
import { useAutonomyStore } from "@/features/autonomy";
import { makeUrl } from "@/util/url";

const store = useAutonomyStore();
let timer: ReturnType<typeof setInterval> | null = null;
let polling = false;
const downloadUrl = computed(() => {
  const status = store.recording;
  return status?.session_id && !status.active
    ? makeUrl(`/px/api/autonomy/recordings/${status.session_id}/download`,
        +(import.meta.env.VITE_WS_APP_PORT || "8001"))
    : null;
});
const refresh = async () => {
  if (polling || store.recordingLoading) return;
  polling = true;
  try { await store.refreshRecording(); }
  finally { polling = false; }
};
onMounted(() => {
  void refresh();
  timer = setInterval(() => void refresh(), 1000);
});
onUnmounted(() => { if (timer) clearInterval(timer); });
</script>
