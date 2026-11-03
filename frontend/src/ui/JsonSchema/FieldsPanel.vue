<template>
  <Fieldset
    v-if="!inhibitFieldset"
    ref="fieldset"
    class="schema-section col-span-full min-w-0 max-w-full"
    :class="{ 'schema-section-flat': level >= 2 }"
    :legend="title || undefined"
    toggleable
    :collapsed="collapsed"
    :id="idPrefix"
  >
    <TextExpandable :level="level" :text="description" />
    <slot></slot>
  </Fieldset>
  <div v-else class="schema-section col-span-full min-w-0 max-w-full">
    <Title :title="title" />
    <TextExpandable :level="level" :text="description" />
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { useTemplateRef } from "vue";
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
const fieldset = useTemplateRef("fieldset");
defineExpose({ expand: () => fieldset.value?.expand() });
</script>

<style scoped>
.schema-section-flat {
  border: 0;
  padding: 0;
}

.schema-section-flat > :deep(.p-fieldset-legend) {
  margin-inline-start: 0;
  padding-inline: 0;
}

.schema-section-flat
  > :deep(.p-fieldset-content-container > .p-fieldset-content) {
  padding-inline: 0;
  padding-bottom: 0;
}
</style>
