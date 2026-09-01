<template>
  <Button
    :aria-label="buttonLabel"
    :icon="buttonIcon"
    v-tooltip.right="buttonLabel"
    text
    @click="router.push({ name: targetRouteName })"
  />
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const router = useRouter();
const route = useRoute();

const isHome = computed(() => route.name === "home");

const buttonIcon = computed(() =>
  isHome.value ? "pi pi-map-marker" : "pi pi-home",
);

const buttonLabel = computed(() =>
  isHome.value ? "Go to autonomy workspace" : "Go to home",
);

const targetRouteName = computed(() => (isHome.value ? "autonomy" : "home"));
</script>
