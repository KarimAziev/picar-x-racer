<template>
  <DataTable :value="items">
    <template #header>
      <ButtonGroup>
        <Button
          outlined
          label="New"
          icon="pi pi-plus"
          class="mr-2"
          @click="handleAddItem"
        />
      </ButtonGroup>
    </template>
    <Column header="Default">
      <template #body="slotProps">
        <Tag v-if="slotProps.data.default" value="Default"></Tag>

        <Tag
          v-else
          v-tooltip="'Click to set as default text'"
          class="cursor-pointer"
          @click="markDefault(slotProps.data)"
          severity="secondary"
          value="Default"
        ></Tag>
      </template>
    </Column>
    <Column field="language" header="Language">
      <template #body="slotProps">
        <SelectField
          :loading="langsLoading"
          fieldClassName="language"
          field="language"
          filter
          optionLabel="label"
          optionValue="value"
          v-model="slotProps.data.language"
          :options="ttsLanguages"
      /></template>
    </Column>

    <Column field="text" header="Text" :colspan="4">
      <template #body="slotProps">
        <Textarea
          class="w-[120px] md:w-[200px]"
          v-tooltip="'Type the text to speech'"
          v-model="slotProps.data.text"
        />
      </template>
    </Column>
    <Column :exportable="false" header="Actions" :colspan="4">
      <template #body="slotProps">
        <ButtonGroup class="whitespace-nowrap">
          <Button
            @click="sayText(slotProps.data)"
            icon="pi pi-play-circle"
            text
            size="small"
            aria-label="Speak"
          />
          <Button
            icon="pi pi-trash"
            size="small"
            severity="danger"
            text
            @click="handleRemove(slotProps.index)"
          />
        </ButtonGroup>
      </template>
    </Column>
  </DataTable>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useSettingsStore, useTTSStore } from "@/features/settings/stores";
import SelectField from "@/ui/SelectField.vue";
import type { TextItem } from "@/features/settings/interface";
import Textarea from "primevue/textarea";
import ButtonGroup from "primevue/buttongroup";

const store = useSettingsStore();
const ttsStore = useTTSStore();

const items = computed(() => store.data.tts.texts);
const ttsLanguages = computed(() => ttsStore.data);
const langsLoading = computed(() => !!ttsStore.loading);

const sayText = async (textItem: TextItem) => {
  if (textItem.text && textItem.text.length) {
    await store.speakText(textItem.text, textItem.language);
  }
};

const handleRemove = (index: number) => {
  store.data.tts.texts = store.data.tts.texts.filter((_, idx) => idx !== index);
  store.saveSettings();
};

const markDefault = (item: TextItem) => {
  if (item.default) {
    delete item.default;
    return;
  }

  store.data.tts.texts.forEach((it) => {
    if (it.default) {
      delete it.default;
    }
    if (item === it) {
      item.default = true;
    }
  });
};

const handleAddItem = () => {
  store.data.tts.texts.push({
    text: "",
    language: items.value[items.value.length - 1]?.language,
  });
};
</script>
