<template>
  <Tabs v-model:value="popupStore.tab" class="robo-tabs" lazy>
    <TabList>
      <Tab :value="SettingsTab.GENERAL">General</Tab>
      <Tab :value="SettingsTab.KEYBINDINGS">Keybindings</Tab>
      <Tab :value="SettingsTab.CALIBRATION">Calibration</Tab>
      <Tab :value="SettingsTab.TTS">TTS</Tab>
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
      <TabPanel :value="SettingsTab.TTS">
        <ScrollPanel class="wrapper">
          <TTSSettings />
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
import TTSSettings from "@/features/settings/components/TTSSettings.vue";
import KeybindingsPanel from "@/features/settings/components/KeybindingsPanel.vue";
import GeneralPanel from "@/features/settings/components/GeneralPanel.vue";
import { SettingsTab } from "@/features/settings/enums";
import { usePopupStore } from "@/features/settings/stores";
import Calibration from "@/features/settings/components/Calibration.vue";

const popupStore = usePopupStore();
</script>
<style scoped lang="scss">
.robo-tabs {
  font-family: var(--font-family-settings);
}
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

:deep(.p-button) {
  font-size: 10px;
  max-width: 100px;
  @media (min-width: 640px) {
    & {
      font-size: 1rem;
    }
  }
}
:deep(td) {
  @media (max-width: 640px) {
    & {
      padding: 0;
      max-width: 30%;
    }
  }
}
:deep(.p-select),
:deep(textarea),
:deep(.p-input) {
  font-size: 10px;
  max-width: 200px;
  @media (min-width: 640px) {
    & {
      font-size: 1rem;
    }
  }
}

:deep(.pi),
:deep(.p-tag) {
  font-size: 10px;
  @media (min-width: 640px) {
    & {
      font-size: 1rem;
    }
  }
}
:deep(.p-button-icon-only) {
  width: 1rem;
  height: 1rem;
  @media (min-width: 640px) {
    & {
      width: 2.5rem;
      height: 2.5rem;
    }
  }
}

:deep(.p-icon) {
  @media (max-width: 640px) {
    & {
      width: 10px;
      height: 10px;
    }
  }
}
:deep(.p-inputnumber-input) {
  font-size: 10px;
  max-width: 100px;
  @media (min-width: 640px) {
    & {
      font-size: 1rem;
    }
  }
}
</style>
