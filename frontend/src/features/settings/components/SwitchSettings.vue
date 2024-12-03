<template>
  <div v-for="(item, field) in toggleableSettings" :key="field" class="field">
    <ToggleSwitch
      @update:model-value="onUpdate"
      :pt="{ input: { id: field } }"
      :v-tooltip="item.description"
      v-model="store.data[field]"
    />
    <label :for="field">{{ item.label }}</label>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import { toggleableSettings } from "@/features/settings/config";
import ToggleSwitch from "primevue/toggleswitch";

const store = useSettingsStore();
const emit = defineEmits(["update:modelValue"]);

const onUpdate = (fieldName: string, newValue: boolean) => {
  emit("update:modelValue", fieldName, newValue);
};
</script>

<style scoped lang="scss">
.field {
  display: flex;
  gap: 10px;
  margin: 10px 0;
}
</style>
