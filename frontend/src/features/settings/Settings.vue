<template>
  <div class="min-h-[35vh]">
    <Tabs v-model:value="popupStore.tab" class="font-sans" lazy scrollable>
      <TabList ref="tabList">
        <Tab :value="SettingsTab.GENERAL">General</Tab>
        <Tab :value="SettingsTab.MODELS">Models</Tab>
        <Tab :value="SettingsTab.ROBOT">Robot</Tab>
        <Tab :value="SettingsTab.KEYBINDINGS" v-if="!isMobile">Keybindings</Tab>
        <Tab :value="SettingsTab.PHOTOS">Photos</Tab>
        <Tab :value="SettingsTab.VIDEOS">Videos</Tab>
        <Tab :value="SettingsTab.MUSIC">Music</Tab>
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
        <TabPanel :value="SettingsTab.ROBOT">
          <RobotPanel />
        </TabPanel>
        <TabPanel :value="SettingsTab.PHOTOS">
          <PhotosPanel />
        </TabPanel>
        <TabPanel :value="SettingsTab.MUSIC">
          <MusicPanel />
        </TabPanel>
        <TabPanel :value="SettingsTab.VIDEOS"><VideoPanel /></TabPanel>
        <TabPanel :value="SettingsTab.TTS">
          <TTSPanel />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, useTemplateRef, onMounted } from "vue";
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
import { isFunction } from "@/util/guards";

const tabListRef = useTemplateRef("tabList");

const TTSPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/TTSPanel.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const MusicPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/MusicPanel.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const VideoPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/VideoPanel.vue"),
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

const RobotPanel = defineAsyncComponent({
  loader: () => import("@/features/settings/components/RobotPanel.vue"),
  loadingComponent: Skeleton,
  errorComponent: ErrorComponent,
  delay: 0,
});

const popupStore = usePopupStore();
const isMobile = useDeviceWatcher();
onMounted(() => {
  setTimeout(() => {
    if (isFunction((tabListRef.value as any)?.updateInkBar)) {
      (tabListRef.value as any)?.updateInkBar();
    }
  }, 1000);
});
</script>
