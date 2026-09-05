<template>
  <InfoBlock>
    <InfoItem label="Speed:" :value="speed" />
    <InfoItem label="Camera Tilt:" :value="camTilt" />
    <InfoItem label="Camera Pan:" :value="camPan" />
    <InfoItem label="Servo Dir:" :value="servoAngle" />
    <template v-for="reading in sensorStore.readings" :key="reading.name">
      <InfoItem
        v-if="!isNull(reading.temperature_c)"
        :label="`${reading.name} temperature:`"
        :value="formatMetric(reading.temperature_c, '°C')"
      />
      <InfoItem
        v-if="!isNull(reading.relative_humidity_percent)"
        :label="`${reading.name} humidity:`"
        :value="formatMetric(reading.relative_humidity_percent, '%')"
      />
      <InfoItem
        v-if="!isNull(reading.pressure_pa)"
        :label="`${reading.name} pressure:`"
        :value="formatMetric(reading.pressure_pa / 100, ' hPa')"
      />
      <InfoItem
        v-if="!isNull(reading.magnetic_field_t)"
        :label="`${reading.name}:`"
        :value="formatMagneticField(reading.magnetic_field_t)"
      />
      <InfoItem
        v-if="reading.error"
        :label="`${reading.name}:`"
        :value="reading.error"
      />
    </template>
    <MaxSpeed />
    <ToggleableView setting="general.show_auto_measure_distance_button">
      <Distance />
    </ToggleableView>
    <ToggleableView setting="general.show_avoid_obstacles_button">
      <AvoidObstacles />
    </ToggleableView>
  </InfoBlock>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useControllerStore } from "@/features/controller/store";

import InfoItem from "@/ui/InfoItem.vue";
import InfoBlock from "@/ui/InfoBlock.vue";
import ToggleableView from "@/ui/ToggleableView.vue";
import Distance from "@/features/controller/components/Distance.vue";
import AvoidObstacles from "@/features/controller/components/AvoidObstacles.vue";
import MaxSpeed from "@/features/controller/components/MaxSpeed.vue";
import { formatDisplayNumber } from "@/util/number";
import { useAuxiliarySensorStore } from "@/features/sensors";
import { isNull } from "@/util/guards";

const store = useControllerStore();
const sensorStore = useAuxiliarySensorStore();

const formatMetric = (value: number, suffix: string) =>
  `${Math.round(value * 10) / 10}${suffix}`;

const formatMagneticField = (value: [number, number, number]) =>
  `${value.map((axis) => Math.round(axis * 1e7) / 10).join(" / ")} µT`;

const camPan = computed(() => formatDisplayNumber(store.camPan));
const camTilt = computed(() => formatDisplayNumber(store.camTilt));
const servoAngle = computed(() => formatDisplayNumber(store.servoAngle));
const speed = computed(() =>
  formatDisplayNumber(store.direction * store.speed),
);

onMounted(sensorStore.fetchReadings);
</script>
