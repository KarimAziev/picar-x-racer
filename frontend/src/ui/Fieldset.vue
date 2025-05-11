<template>
  <FieldsetPrimevue
    :toggleable="toggleable"
    :legend="legend || header"
    :collapsed="isCollapsed"
    @update:collapsed="handleUpdateCollapsed"
  >
    <template #legend="scope" v-if="$slots.legend">
      <slot name="legend" :toggleCallback="scope.toggleCallback" />
    </template>
    <slot></slot>
  </FieldsetPrimevue>
</template>

<script setup lang="ts">
import FieldsetPrimevue from "primevue/fieldset";
import { useLocalStorage } from "@vueuse/core";

export interface Props {
  toggleable?: boolean;
  collapsed?: boolean;
  legend?: string;
  header?: string;
  id: string;
}

const props = withDefaults(defineProps<Props>(), {
  toggleable: true,
});

const isCollapsed = useLocalStorage(props.id, props.collapsed);

const emit = defineEmits(["update:collapsed"]);

const handleUpdateCollapsed = (value: boolean) => {
  isCollapsed.value = value;
  emit("update:collapsed", value);
};

const expand = () => {
  handleUpdateCollapsed(false);
};

const collapse = () => {
  handleUpdateCollapsed(true);
};

defineExpose({
  collapse,
  expand,
  isCollapsed,
});
</script>
