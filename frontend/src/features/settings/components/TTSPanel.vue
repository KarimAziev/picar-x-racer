<template>
  <SelectField
    fieldClassName="min-w-[150px]"
    field="default_tts_language"
    label="Default Language"
    filter
    optionLabel="label"
    optionValue="value"
    :loading="langsLoading"
    v-model="store.data.tts.default_tts_language"
    :options="ttsLanguages"
  />
  <Panel header="Allowed languages" toggleable>
    <LangsPickList v-if="!langsLoading" />
  </Panel>
  <Panel header="Texts presets" toggleable>
    <TextsTable />
  </Panel>
</template>

<script setup lang="ts">
import { onMounted, computed } from "vue";
import { useTTSStore, useSettingsStore } from "@/features/settings/stores";
import Panel from "@/ui/Panel.vue";
import TextsTable from "@/features/settings/components/tts/TextsTable.vue";
import SelectField from "@/ui/SelectField.vue";
import LangsPickList from "@/features/settings/components/tts/LangsPickList.vue";

const store = useSettingsStore();
const ttsStore = useTTSStore();
const ttsLanguages = computed(() => ttsStore.data);
const langsLoading = computed(() => !!ttsStore.loading);

onMounted(ttsStore.fetchLanguagesOnce);
</script>
