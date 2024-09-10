<template>
  <Tabs v-model:value="popupStore.tab" class="robo-tabs" lazy>
    <TabList>
      <Tab :value="SettingsTab.GENERAL">General</Tab>
      <Tab :value="SettingsTab.KEYBINDINGS">Keybindings</Tab>
      <Tab :value="SettingsTab.CALIBRATION">Calibration</Tab>
    </TabList>
    <TabPanels>
      <TabPanel :value="SettingsTab.GENERAL">
        <ScrollPanel class="wrapper">
          <GeneralPanel />
        </ScrollPanel>
      </TabPanel>
      <TabPanel :value="SettingsTab.KEYBINDINGS">
        <ScrollPanel class="wrapper">
          <KeybindingsPanel />
        </ScrollPanel>
      </TabPanel>
      <TabPanel :value="SettingsTab.CALIBRATION">
        <ScrollPanel class="wrapper">
          <Calibration />
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
import KeybindingsPanel from "@/features/settings/components/KeybindingsPanel.vue";
import GeneralPanel from "@/features/settings/components/GeneralPanel.vue";
import { SettingsTab } from "@/features/settings/enums";
import { usePopupStore } from "@/features/settings/stores";
import Calibration from "@/features/settings/components/Calibration.vue";

const popupStore = usePopupStore();
</script>
<style scoped lang="scss">
.wrapper {
  width: 300px;
}
@media (min-width: 500px) {
  .wrapper {
    width: 400px;
  }
}
@media (min-width: 840px) {
  .wrapper {
    width: 740px;
  }
}
.robo-tabs {
  font-family: var(--font-family-settings);
}
</style>
