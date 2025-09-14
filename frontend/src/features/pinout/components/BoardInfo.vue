<template>
  <div
    v-if="boardInfo"
    class="flex items-center gap-4 p-3 rounded-lg shadow-sm"
  >
    <Avatar
      :label="boardInfo.model"
      shape="circle"
      class="w-12 h-12"
      size="xlarge"
    />

    <div class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-3">
        <div class="truncate">
          <div
            class="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate"
          >
            {{ boardInfo.manufacturer }} {{ boardInfo.model }}
            <span
              class="ml-2 text-xs font-medium text-gray-500 dark:text-gray-400"
            >
              · {{ boardInfo.soc }}
            </span>
          </div>
          <div class="text-xs text-gray-500 dark:text-gray-400 truncate">
            PCB {{ boardInfo.pcb_revision }} · rev {{ boardInfo.revision }} ·
            {{ boardInfo.released }}
          </div>
        </div>

        <div class="flex items-center gap-2">
          <Tag class="text-xs" :value="memoryLabel" severity="info" />
          <Tag class="text-xs" :value="boardInfo.storage" severity="warning" />
        </div>
      </div>

      <div class="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <div
          class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200"
        >
          <i class="pi pi-usb text-xs"></i>
          <span class="font-medium">{{ boardInfo.usb }} USB</span>
          <span v-if="boardInfo.usb3" class="ml-1 text-slate-500">
            ({{ boardInfo.usb3 }} USB3)
          </span>
        </div>

        <div
          class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200"
        >
          <i class="pi pi-sitemap text-xs"></i>
          <span class="font-medium">
            {{ boardInfo.ethernet }}× {{ boardInfo.eth_speed }} Mb/s
          </span>
        </div>

        <div
          class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200"
        >
          <i class="pi pi-camera text-xs"></i>
          <span class="font-medium">
            {{ boardInfo.csi }} CSI · {{ boardInfo.dsi }} DSI
          </span>
        </div>

        <div
          class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200"
        >
          <i
            class="pi pi-wifi text-xs"
            :class="boardInfo.wifi ? 'text-primary-500' : 'text-gray-400'"
          ></i>
          <span class="font-medium">
            {{ boardInfo.wifi ? "Wi-Fi" : "No Wi-Fi" }}
          </span>
          <span v-if="boardInfo.bluetooth" class="ml-2 text-slate-500">
            · Bluetooth
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useStore as usePinoutStore } from "@/features/pinout/store";
import type { BoardMetadata } from "@/features/pinout/store";

const deviceStore = usePinoutStore();
const boardInfo = computed<BoardMetadata | null>(() => deviceStore.board);

const memoryLabel = computed(() => {
  if (!boardInfo.value) return "";
  const mem = boardInfo.value.memory;

  if (mem >= 1024) return `${Math.round(mem / 1024)} GB`;
  return `${mem} MB`;
});

onMounted(deviceStore.fetchDataOnce);
</script>
