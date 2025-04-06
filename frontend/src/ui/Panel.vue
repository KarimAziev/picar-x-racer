<template>
  <Panel v-bind="props" ref="panelRef">
    <template #header>
      <div
        class="flex-auto text-left leading-none font-semibold cursor-pointer"
        @click="handleToggle"
      >
        {{ legend || header }}
      </div>
    </template>
    <slot></slot>
  </Panel>
</template>

<script setup lang="ts">
import Panel, { PanelProps } from "primevue/panel";
import { ref, computed } from "vue";

interface Props extends PanelProps {
  toggleable?: boolean;
  legend?: string;
}

const props = defineProps<Props>();

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
}
</style>
