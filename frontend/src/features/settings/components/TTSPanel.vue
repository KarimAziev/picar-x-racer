<template>
  <div>
    Default Language
    <SelectField
      fieldClassName="w-[100px]"
      field="default_tts_language"
      filter
      optionLabel="label"
      optionValue="value"
      v-model="store.data.tts.default_tts_language"
      :options="ttsLanguages"
    />
  </div>
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
        <Button
          label="Save"
          icon="pi pi-save"
          class="mr-2"
          @click="saveSettings"
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
import { useSettingsStore } from "@/features/settings/stores";
import Textarea from "primevue/textarea";
import { computed } from "vue";
import ButtonGroup from "primevue/buttongroup";

import { ttsLanguages } from "@/features/settings/config";
import SelectField from "@/ui/SelectField.vue";
import { TextItem } from "@/features/settings/stores/settings";

const store = useSettingsStore();

const items = computed(() => store.data.tts.texts);

function saveSettings() {
  store.saveSettings();
}

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
