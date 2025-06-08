<template>
  <Fieldset
    v-if="!inhibitFieldset"
    :legend="title ? startCase(title) : undefined"
    toggleable
    :collapsed="collapsed"
    :id="idPrefix"
  >
    <TextExpandable :level="level" :text="description" />
    <slot></slot>
  </Fieldset>
  <div v-else>
    <Title :title="title" />
    <TextExpandable :level="level" :text="description" />
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { startCase } from "@/util/str";
import Title from "@/ui/JsonSchema/Title.vue";
import TextExpandable from "@/ui/JsonSchema/TextExpandable.vue";
import Fieldset from "@/ui/Fieldset.vue";

defineProps<{
  level: number;
  inhibitFieldset?: boolean;
  title?: string;
  collapsed: boolean;
  idPrefix: string;
  description?: string;
}>();
</script>
