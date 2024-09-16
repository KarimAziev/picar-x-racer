<template>
  <DataTable :value="items">
    <template #header>
      <ButtonGroup>
        <Button
          outlined
          label="New"
          icon="pi pi-plus"
          severity="success"
          class="mr-2"
          @click="handleAddItem"
        />
        <Button
          label="Save"
          icon="pi pi-save"
          severity="success"
          class="mr-2"
          @click="saveSettings"
        />
      </ButtonGroup>
    </template>
    <Column header="Default">
      <template #body="slotProps">
        <Tag
          v-if="slotProps.data.default"
          severity="success"
          value="Default"
        ></Tag>

        <Tag
          v-else
          v-tooltip="'Click to make it default text'"
          class="tag"
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
          v-model="slotProps.data.language"
          :options="ttsLanguages"
          :simpleOptions="true"
      /></template>
    </Column>

    <Column field="text" header="Text">
      <template #body="slotProps">
        <Textarea
          v-tooltip="'Type the text to speech'"
          v-model="slotProps.data.text"
        />
      </template>
    </Column>
    <Column :exportable="false" header="Actions">
      <template #body="slotProps">
        <ButtonGroup>
          <Button
            @click="sayText(slotProps.data)"
            icon="pi pi-play-circle"
            text
            raised
            rounded
            aria-label="Speak"
          />
          <Button
            icon="pi pi-trash"
            outlined
            rounded
            severity="danger"
            text
            raised
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

const items = computed(() => store.settings.texts);

function saveSettings() {
  store.saveTexts();
}

const sayText = async (textItem: TextItem) => {
  if (textItem.text && textItem.text.length) {
    await store.speakText(textItem.text, textItem.language);
  }
};

const handleRemove = (index: number) => {
  store.settings.texts = store.settings.texts.filter((_, idx) => idx !== index);
  store.saveTexts();
};

const markDefault = (item: TextItem) => {
  if (item.default) {
    delete item.default;
    return;
  }
  store.settings.texts.forEach((it) => {
    if (it.default) {
      delete it.default;
    }
    if (item === it) {
      item.default = true;
    }
  });
};

const handleAddItem = () => {
  store.settings.texts.push({
    text: "",
    language: items.value[items.value.length - 1]?.language,
  });
};
</script>

<style scoped lang="scss">
.tag {
  cursor: pointer;
}
.language {
  width: 60px;
}
textarea {
  width: 100px;
}
@media (min-width: 768px) {
  textarea {
    width: 350px;
  }
  .language {
    width: 100px;
  }
}

@media (min-width: 1200px) {
  textarea {
    width: 350px;
  }
}
</style>
