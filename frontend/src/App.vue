<template>
  <NavDrawer />
  <RouterView />
</template>

<script setup lang="ts">
import { RouterView } from "vue-router";

import NavDrawer from "@/components/NavDrawer.vue";
</script>
