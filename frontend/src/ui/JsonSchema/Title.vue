<template>
  <h4 class="font-bold" v-if="title">
    {{ startCase(title) }}
  </h4>
</template>

<script setup lang="ts">
import { startCase } from "@/util/str";
defineProps<{ title?: string }>();
</script>
