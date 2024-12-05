<template>
  <Field
    v-for="(item, field) in fields"
    :key="field"
    :label="item.label"
    layout="row-reverse"
  >
    <ToggleSwitch
      @update:model-value="onUpdate"
      :pt="{ input: { id: field } }"
      v-model="store.data[field]"
    />
  </Field>

  <slot></slot>
</template>

<script setup lang="ts">
import Field from "@/ui/Field.vue";
import ToggleSwitch from "primevue/toggleswitch";

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
