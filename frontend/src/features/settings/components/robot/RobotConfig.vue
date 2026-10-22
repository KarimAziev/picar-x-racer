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
        :disabled="loading || !store.config"
        size="small"
        label="Export"
        icon="pi pi-download"
        type="button"
        outlined
        title="Download robot configuration, including unsaved edits"
        @click="handleExport"
        class="w-fit"
      />
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
import { onMounted, ref, watch, computed, provide } from "vue";
import { useRobotStore } from "@/features/settings/stores";
import { cloneDeep } from "@/util/obj";
import { isDataChangedPred } from "@/features/settings/components/robot/util";
import { validateAll, resolveRefRecursive } from "@/ui/JsonSchema/util";
import { isPlainObject } from "@/util/guards";
import JsonSchema from "@/ui/JsonSchema/JsonSchema.vue";
import Loader from "@/features/settings/components/robot/Loader.vue";
import { pinAssignmentsKey } from "@/features/pinout/context";
import { collectPinAssignments } from "@/features/pinout/usage";

defineProps<{ idPrefix: string }>();

const store = useRobotStore();
const currValue = ref(cloneDeep(store.data));

provide(
  pinAssignmentsKey,
  computed(() => collectPinAssignments(store.config, currValue.value)),
);

const handleExport = () => {
  const blob = new Blob([JSON.stringify(currValue.value, null, 2) + "\n"], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "robot-config.json";
  document.body.append(link);
  try {
    link.click();
  } finally {
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
};

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

const invalidData = computed(() =>
  !resolvedSchemas.value
    ? null
    : validateAll(
        resolvedSchemas.value,
        currValue.value,
        resolvedSchemas.value?.$defs,
      ),
);

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
    loading.value = false;
  }
});
</script>
