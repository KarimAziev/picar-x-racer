<template>
  <Panel header="Appearance" toggleable>
    <SwitchSettings />
    <div class="field">
      <label for="auto_measure_distance_delay_ms"
        >Auto Measure Distance Delay in Milliseconds</label
      >
      <InputNumber
        class="input-number"
        inputId="auto_measure_distance_delay_ms"
        :min="50"
        :pt="{ pcInput: { id: 'auto_measure_distance_delay_ms' } }"
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
  <Music collapsed toggleable header="Music" />
  <Panel header="Photos" toggleable collapsed>
    <Images />
  </Panel>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";

import InputNumber from "primevue/inputnumber";

import Music from "@/features/settings/components/Music.vue";
import Images from "@/features/settings/components/Images.vue";
import SwitchSettings from "@/features/settings/components/SwitchSettings.vue";
import VideoSettings from "@/features/settings/components/VideoSettings.vue";
import Panel from "@/ui/Panel.vue";

const store = useSettingsStore();
</script>

<style scoped lang="scss">
.field {
  label {
    display: block;
  }
}
</style>
