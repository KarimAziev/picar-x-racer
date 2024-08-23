<template>
  <Tabs v-model:value="popupStore.tab" lazy>
    <TabList>
      <Tab :value="SettingsTab.GENERAL">General</Tab>
      <Tab :value="SettingsTab.KEYBINDINGS">Keybindings</Tab>
    </TabList>
    <TabPanels>
      <TabPanel :value="SettingsTab.GENERAL">
        <GeneralPanel />
      </TabPanel>
      <TabPanel :value="SettingsTab.KEYBINDINGS">
        <KeybindingsPanel />
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

const popupStore = usePopupStore();
</script>
<style scoped lang="scss">
.p-tab-active {
  color: var(--color-text);
}
.p-tab {
}
</style>
