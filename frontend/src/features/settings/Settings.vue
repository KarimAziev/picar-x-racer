<template>
  <Tabs value="0">
    <TabList>
      <Tab value="0">General</Tab>
      <Tab value="1">Keybindings</Tab>
    </TabList>
    <TabPanels>
      <TabPanel value="0">
        <GeneralPanel />
      </TabPanel>
      <TabPanel value="1">
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
</script>
