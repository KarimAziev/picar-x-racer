<template>
  <InfoBlock>
    <InfoItem label="Speed:" :value="speed" />
    <InfoItem label="Camera Tilt:" :value="camTilt" />
    <InfoItem label="Camera Pan:" :value="camPan" />
    <InfoItem label="Servo Dir:" :value="servoAngle" />
    <InfoItem label="Max Speed:" :value="maxSpeed" />
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

const store = useControllerStore();

const camPan = computed(() => store.camPan.toString().padStart(2, "0"));
const camTilt = computed(() => store.camTilt.toString().padStart(2, "0"));
const servoAngle = computed(() => store.servoAngle.toString().padStart(2, "0"));

const speed = computed(() =>
  (store.direction * store.speed).toString().padStart(2, "0"),
);

const maxSpeed = computed(() => store.maxSpeed);
</script>
