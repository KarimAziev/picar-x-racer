<template>
  <InfoItem label="Max Speed:" :value="maxSpeed">
    <template #value="slotProps">
      <span class="relative flex items-center">
        <ButtonIcon
          v-tooltip="'Decrease max speed'"
          :disabled="decDisabled"
          @click="handleDecMaxSpeed"
          class="px-2"
          ><template #icon>&#8722;</template></ButtonIcon
        >

        <span class="relative"
          >{{ slotProps.value }}
          <ButtonIcon
            v-tooltip="'Increase max speed'"
            class="px-2 absolute top-0"
            :disabled="incDisabled"
            @click="handleIncMaxSpeed"
            ><template #icon>&#43;</template></ButtonIcon
          ></span
        >
      </span>
    </template>
  </InfoItem>
</template>

<script setup lang="ts">
import { computed } from "vue";
import InfoItem from "@/ui/InfoItem.vue";
import ButtonIcon from "@/ui/ButtonIcon.vue";
import { useControllerStore, MIN_SPEED } from "@/features/controller/store";
import { useRobotStore } from "@/features/settings/stores";

const store = useControllerStore();
const robotStore = useRobotStore();
const maxSpeed = computed(() => store.maxSpeed);
const decDisabled = computed(() => maxSpeed.value <= MIN_SPEED);
const incDisabled = computed(() => maxSpeed.value >= robotStore.maxSpeed);

const handleDecMaxSpeed = () => {
  store.decreaseMaxSpeed();
};

const handleIncMaxSpeed = () => {
  store.increaseMaxSpeed();
};
</script>
