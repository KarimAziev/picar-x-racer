<template>
  <Panel class="p-panel" v-bind="props" ref="panelRef">
    <template #header>
      <div class="header" @click="handleToggle">{{ header }}</div>
    </template>
    <slot></slot>
  </Panel>
</template>

<script setup lang="ts">
import Panel, { PanelProps } from "primevue/panel";
import { ref, computed } from "vue";

const props = defineProps<PanelProps>();

const header = computed(() => props.header);

const panelRef = ref();
const handleToggle = () => {
  panelRef.value?.toggle();
};
</script>

<style scoped lang="scss">
:deep(.p-panel-header) {
  display: flex;
  flex-direction: row-reverse;
  .header {
    flex: auto;
    text-align: left;
    line-height: 1;
    font-weight: 600;
    cursor: pointer;
  }
}
</style>
