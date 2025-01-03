<template>
  <ToggleSwitchField
    v-for="(item, field) in fields"
    :key="field"
    :label="item.label"
    v-tooltip="item.description"
    layout="row-reverse"
    field-class-name="flex-row-reverse gap-2.5 items-center justify-end my-1"
    @update:model-value="(value) => onUpdate(field as string, value)"
    :field="field as string"
    v-model="store.data[scope][field]"
  />

  <slot></slot>
</template>

<script setup lang="ts">
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";

const emit = defineEmits(["update:modelValue"]);

type ToggleableConfig = {
  [key: string]: { label?: string; description?: string };
};

type MappedData = {
  [P in keyof ToggleableConfig]?: unknown;
};

interface StoreData {
  data: Record<string, MappedData>;
}

defineProps<{
  store: StoreData;
  fields: ToggleableConfig;
  scope: keyof MappedData;
}>();

const onUpdate = (fieldName: string, newValue: boolean) => {
  emit("update:modelValue", fieldName, newValue);
};
</script>
