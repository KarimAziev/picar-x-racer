<template>
  <ToggleSwitchField
    v-for="(item, field) in fields"
    :key="field"
    :label="item.label"
    layout="row-reverse"
    @update:model-value="(value) => onUpdate(field as string, value)"
    :pt="{ input: { id: field } }"
    v-model="store.data[field]"
  />

  <slot></slot>
</template>

<script setup lang="ts">
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";

const emit = defineEmits(["update:modelValue"]);

type ToggleableConfig = { [key: string]: { label?: string } };
type MappedData = {
  [P in keyof ToggleableConfig]?: unknown;
};
interface StoreData {
  data: MappedData;
}

defineProps<{ store: StoreData; fields: ToggleableConfig }>();

const onUpdate = (fieldName: string, newValue: boolean) => {
  emit("update:modelValue", fieldName, newValue);
};
</script>
