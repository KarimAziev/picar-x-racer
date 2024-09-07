<template>
  <div v-if="avoidObstacles" class="info">
    <InfoItem label="Autopilot is on" />
  </div>
  <InfoBlock v-else>
    <InfoItem label="Camera Tilt" :value="camTilt" value-suffix="°" />
    <InfoItem label="Camera Pan" :value="camPan" value-suffix="°" />
    <InfoItem label="Servo Direction" :value="servoAngle" value-suffix="°" />
    <InfoItem label="Max Speed" :value="maxSpeed" />
  </InfoBlock>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useControllerStore } from "@/features/controller/store";

import InfoItem from "@/ui/InfoItem.vue";
import InfoBlock from "@/ui/InfoBlock.vue";

const store = useControllerStore();

const avoidObstacles = computed(() => store.avoidObstacles);

const camPan = computed(() => store.camPan);
const camTilt = computed(() => store.camTilt);
const servoAngle = computed(() => store.servoAngle);

const maxSpeed = computed(() => store.maxSpeed);
</script>
