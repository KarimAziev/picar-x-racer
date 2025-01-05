<template>
  <Tabs v-model:value="popupStore.tab" class="font-sans" lazy>
    <TabList>
      <Tab :value="SettingsTab.GENERAL">General</Tab>
      <Tab :value="SettingsTab.MODELS">Models</Tab>
      <Tab :value="SettingsTab.KEYBINDINGS" v-if="!isMobile">Keybindings</Tab>
      <Tab :value="SettingsTab.CALIBRATION">Calibration</Tab>
      <Tab :value="SettingsTab.PHOTOS">Photos</Tab>
      <Tab :value="SettingsTab.TTS">TTS</Tab>
    </TabList>
    <TabPanels>
      <TabPanel :value="SettingsTab.GENERAL">
        <GeneralPanel />
      </TabPanel>
      <TabPanel :value="SettingsTab.MODELS">
        <ModelsPanel />
      </TabPanel>
      <TabPanel :value="SettingsTab.KEYBINDINGS" v-if="!isMobile">
        <KeybindingsPanel />
      </TabPanel>
      <TabPanel :value="SettingsTab.CALIBRATION">
        <CalibrationPanel />
      </TabPanel>
      <TabPanel :value="SettingsTab.PHOTOS">
        <PhotosPanel />
      </TabPanel>
      <TabPanel :value="SettingsTab.TTS">
        <TTSPanel />
      </TabPanel>
    </TabPanels>
  </Tabs>
</template>

<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import { SettingsTab } from "@/features/settings/enums";
import { usePopupStore } from "@/features/settings/stores";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import Tabs from "primevue/tabs";
import TabList from "primevue/tablist";
import Tab from "primevue/tab";
import TabPanels from "primevue/tabpanels";
import TabPanel from "primevue/tabpanel";
import Skeleton from "@/ui/Skeleton.vue";
import ErrorComponent from "@/ui/ErrorComponent.vue";

const TTSPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/TTSPanel.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const KeybindingsPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/KeybindingsPanel.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const GeneralPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/GeneralPanel.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const CalibrationPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/CalibrationPanel.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const PhotosPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/PhotosPanel.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const ModelsPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/ModelsPanel.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const popupStore = usePopupStore();
const isMobile = useDeviceWatcher();
</script>
