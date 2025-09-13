<template>
  <Loader v-if="!store.config && loading" />
  <JsonSchema
    v-else-if="store.config"
    v-for="(propSchema, propName) in store.config.properties"
    :level="0"
    :schema="propSchema"
    :invalidData="invalidData"
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

import { useRobotStore, useDeviceInfoStore } from "@/features/settings/stores";
import JsonSchema from "@/ui/JsonSchema/JsonSchema.vue";
import { cloneDeep } from "@/util/obj";
import { isDataChangedPred } from "@/features/settings/components/robot/util";
import type { Data } from "@/features/settings/stores/robot";
import { validateAll, resolveRefRecursive } from "@/ui/JsonSchema/util";
import { isPlainObject } from "@/util/guards";
import Loader from "@/features/settings/components/robot/Loader.vue";

defineProps<{ idPrefix: string }>();

const store = useRobotStore();
const deviceInfoStore = useDeviceInfoStore();
const currValue = ref(cloneDeep(store.data));

const handleSave = async () => {
  await store.saveData(currValue.value);
};

const loading = ref(!store.config);

const resolvedSchemas = computed(() => {
  if (!store.config || !store.config["$defs"]) {
    return null;
  }
  return resolveRefRecursive(
    cloneDeep(store.config),
    cloneDeep(store.config["$defs"]),
  );
});

const invalidData = computed(() => {
  if (!resolvedSchemas.value) {
    return null;
  }

  return validateAll(resolvedSchemas.value, currValue.value);
});

const disabled = computed(() => {
  if (isPlainObject(invalidData.value)) {
    return true;
  }
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
  if (!store.config) {
    loading.value = true;
    await store.fetchFieldsConfig();
    await deviceInfoStore.fetchDataOnce();
    loading.value = false;
  }
});
</script>
