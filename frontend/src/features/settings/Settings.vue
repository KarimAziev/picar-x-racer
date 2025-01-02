<template>
  <Tabs v-model:value="popupStore.tab" class="robo-tabs" lazy>
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
        <ScrollPanel class="wrapper">
          <GeneralPanel />
        </ScrollPanel>
      </TabPanel>
      <TabPanel :value="SettingsTab.MODELS">
        <ScrollPanel class="wrapper">
          <ModelsPanel />
        </ScrollPanel>
      </TabPanel>
      <TabPanel :value="SettingsTab.KEYBINDINGS" v-if="!isMobile">
        <ScrollPanel class="wrapper">
          <KeybindingsPanel />
        </ScrollPanel>
      </TabPanel>
      <TabPanel :value="SettingsTab.CALIBRATION">
        <ScrollPanel class="wrapper">
          <CalibrationPanel />
        </ScrollPanel>
      </TabPanel>
      <TabPanel :value="SettingsTab.PHOTOS">
        <ScrollPanel class="wrapper">
          <PhotosPanel />
        </ScrollPanel>
      </TabPanel>
      <TabPanel :value="SettingsTab.TTS">
        <ScrollPanel class="wrapper">
          <TTSPanel />
        </ScrollPanel>
      </TabPanel>
    </TabPanels>
  </Tabs>
</template>

<script setup lang="ts">
import Tabs from "primevue/tabs";
import TabList from "primevue/tablist";
import Tab from "primevue/tab";
import TabPanels from "primevue/tabpanels";
import TabPanel from "primevue/tabpanel";
import { SettingsTab } from "@/features/settings/enums";
import { usePopupStore } from "@/features/settings/stores";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import TTSPanel from "@/features/settings/components/TTSPanel.vue";
import KeybindingsPanel from "@/features/settings/components/KeybindingsPanel.vue";
import GeneralPanel from "@/features/settings/components/GeneralPanel.vue";
import CalibrationPanel from "@/features/settings/components/CalibrationPanel.vue";
import PhotosPanel from "@/features/settings/components/PhotosPanel.vue";
import ModelsPanel from "@/features/settings/components/ModelsPanel.vue";

const popupStore = usePopupStore();
const isMobile = useDeviceWatcher();
</script>
<style scoped lang="scss">
.robo-tabs {
  font-family: var(--font-family-settings);
}
.robo-tabs {
  width: 98%;
  margin: auto;

  @media (min-width: 400px) {
    width: 370px;
  }

  @media (min-width: 480px) {
    width: 450px;
  }
  @media (min-width: 576px) {
    width: 460px;
  }

  @media (min-width: 768px) {
    width: 600px;
  }
}
</style>
