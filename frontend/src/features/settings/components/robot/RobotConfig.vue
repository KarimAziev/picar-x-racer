<template>
  <div v-if="loading && !store.config"><ProgressSpinner /></div>
  <JsonSchema
    v-else-if="store.config"
    v-for="(propSchema, propName) in store.config.properties"
    :level="0"
    :schema="propSchema"
    :model="currValue"
    :origModel="store.data"
    :path="[propName]"
    :defs="store.config['$defs']"
    :idPrefix="`${idPrefix}-${propName}`"
    :data-comparator="isDataChangedPred"
    @handle-save="store.updatePartialData"
  />
  <Teleport to="#settings-footer">
    <span class="flex gap-2 justify-self-start">
      <Button
        :disabled="loading || disabled"
        size="small"
        label="Save"
        type="submit"
        @click="handleSave"
        class="w-fit"
      />
    </span>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, computed } from "vue";
import ProgressSpinner from "primevue/progressspinner";

import { useRobotStore } from "@/features/settings/stores";
import JsonSchema from "@/ui/JsonSchema/JsonSchema.vue";
import { cloneDeep } from "@/util/obj";
import { isDataChangedPred } from "@/features/settings/components/robot/util";
import type { Data } from "@/features/settings/stores/robot";

defineProps<{ idPrefix: string }>();

const store = useRobotStore();
const currValue = ref(cloneDeep(store.data));

const handleSave = async () => {
  await store.saveData(currValue.value);
};

const loading = ref(true);

const disabled = computed(() => {
  const diff =
    store.data && currValue.value
      ? isDataChangedPred(store.data, currValue.value)
      : false;

  return !diff;
});

watch(
  () => store.data,
  (newVal) => {
    if (store.partialData) {
      currValue.value = {
        ...currValue.value,
        ...cloneDeep(store.partialData),
      };

      delete store.partialData;
    } else {
      currValue.value = cloneDeep(newVal);
    }
  },
  { deep: true, immediate: true },
);

onMounted(async () => {
  loading.value = true;
  await store.fetchFieldsConfig();
  loading.value = false;
});
</script>
