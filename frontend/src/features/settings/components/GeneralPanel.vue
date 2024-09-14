<template>
  <Panel header="Appearance" toggleable>
    <SwitchSettings />
    <div class="field">
      <label for="auto_measure_distance_delay_ms"
        >Auto Measure Distance Delay in Milliseconds</label
      >
      <InputNumber
        class="input-number"
        :min="50"
        :step="50"
        showButtons
        v-tooltip="
          'Amount of milliseconds to wait between reading distance when auto measure distance mode is on.'
        "
        v-model="store.settings.auto_measure_distance_delay_ms"
      />
      <VideoSettings />
    </div>
  </Panel>
  <TTSSettings />

  <Music toggleable header="Music" />
  <Panel header="Photos" toggleable collapsed>
    <Images />
  </Panel>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import Panel from "primevue/panel";

import InputNumber from "primevue/inputnumber";

import Music from "@/features/settings/components/Music.vue";
import Images from "@/features/settings/components/Images.vue";
import SwitchSettings from "@/features/settings/components/SwitchSettings.vue";
import VideoSettings from "@/features/settings/components/VideoSettings.vue";
import TTSSettings from "@/features/settings/components/TTSSettings.vue";

const store = useSettingsStore();
</script>

<style scoped lang="scss">
.field {
  display: flex;
  flex-direction: column;
  margin: 1rem 0;
  .input-number,
  textarea,
  input {
    font-size: 10px;
  }
  @media (min-width: 640px) {
    .input-number,
    textarea,
    input {
      font-size: 1rem;
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
