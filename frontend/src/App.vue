<template>
  <RouterView />
  <Messager />
</template>

<script setup lang="ts">
import { RouterView } from "vue-router";
import Messager from "@/features/messager/Messager.vue";
</script>
