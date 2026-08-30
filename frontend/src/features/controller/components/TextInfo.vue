<template>
  <InfoBlock>
    <InfoItem label="Speed:" :value="speed" />
    <InfoItem label="Camera Tilt:" :value="camTilt" />
    <InfoItem label="Camera Pan:" :value="camPan" />
    <InfoItem label="Servo Dir:" :value="servoAngle" />
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
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";

import InfoItem from "@/ui/InfoItem.vue";
import InfoBlock from "@/ui/InfoBlock.vue";
import ToggleableView from "@/ui/ToggleableView.vue";
import Distance from "@/features/controller/components/Distance.vue";
import AvoidObstacles from "@/features/controller/components/AvoidObstacles.vue";
import MaxSpeed from "@/features/controller/components/MaxSpeed.vue";
import { formatDisplayNumber } from "@/util/number";

const store = useControllerStore();

const camPan = computed(() => formatDisplayNumber(store.camPan));
const camTilt = computed(() => formatDisplayNumber(store.camTilt));
const servoAngle = computed(() => formatDisplayNumber(store.servoAngle));
const speed = computed(() =>
  formatDisplayNumber(store.direction * store.speed),
);
</script>
