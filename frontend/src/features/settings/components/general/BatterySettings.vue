<template>
  <div class="wrapper">
    <div class="column">
      <NumberInputField
        :step="10"
        :min="10"
        field="auto_measure_seconds"
        label="Auto Measure Interval (seconds)"
        v-tooltip="'The time interval between battery measurement cycles.'"
        v-model="store.data.battery.auto_measure_seconds"
      />
      <NumberInputField
        :step="0.1"
        v-tooltip="
          'The duration for which cached values are stored before refreshing.'
        "
        :min="0.1"
        field="cache_seconds"
        label="Cache Seconds"
        v-model="store.data.battery.cache_seconds"
      />
      <NumberInputField
        mode="decimal"
        :step="0.1"
        v-tooltip="'The upper limit for the full battery voltage.'"
        :min="store.data.battery.warn_voltage"
        field="full_voltage"
        label="Full Voltage"
        v-model="store.data.battery.full_voltage"
      />
    </div>

    <div class="column">
      <NumberInputField
        v-tooltip="'The voltage level at which a warning should be triggered.'"
        :step="0.1"
        mode="decimal"
        :max="store.data.battery.full_voltage"
        :min="store.data.battery.danger_voltage"
        field="warn_voltage"
        label="Warn Voltage"
        v-model="store.data.battery.warn_voltage"
      />
      <NumberInputField
        :step="0.1"
        v-tooltip="
          'The voltage level below which the battery is considered in a dangerous state.'
        "
        mode="decimal"
        :max="store.data.battery.warn_voltage"
        :min="store.data.battery.min_voltage"
        field="danger_voltage"
        label="Danger Voltage"
        v-model="store.data.battery.danger_voltage"
      />
      <NumberInputField
        :step="0.1"
        mode="decimal"
        v-tooltip="'The minimum voltage level for the battery.'"
        :max="store.data.battery.danger_voltage"
        :min="1"
        field="min_voltage"
        label="Minimal Voltage"
        v-model="store.data.battery.min_voltage"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";

import NumberInputField from "@/ui/NumberInputField.vue";

const store = useSettingsStore();
</script>
<style scoped lang="scss">
@use "@/assets/scss/two-column-layout.scss";
</style>
