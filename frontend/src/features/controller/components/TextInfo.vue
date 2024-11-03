<template>
  <div v-if="avoidObstacles" class="info">
    <InfoItem label="Autopilot is on" />
  </div>
  <InfoBlock v-else>
    <InfoItem label="Speed:" :value="speed" />
    <InfoItem label="Camera Tilt:" :value="camTilt" />
    <InfoItem label="Camera Pan:" :value="camPan" />
    <InfoItem label="Servo Dir:" :value="servoAngle" />
    <InfoItem label="Max Speed:" :value="maxSpeed" />
  </InfoBlock>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";

import InfoItem from "@/ui/InfoItem.vue";
import InfoBlock from "@/ui/InfoBlock.vue";

const store = useControllerStore();

const avoidObstacles = computed(() => store.avoidObstacles);

const camPan = computed(() => store.camPan.toString().padStart(2, "0"));
const camTilt = computed(() => store.camTilt.toString().padStart(2, "0"));
const servoAngle = computed(() => store.servoAngle.toString().padStart(2, "0"));

const speed = computed(() =>
  (store.direction * store.speed).toString().padStart(2, "0"),
);

const maxSpeed = computed(() => store.maxSpeed);
</script>
