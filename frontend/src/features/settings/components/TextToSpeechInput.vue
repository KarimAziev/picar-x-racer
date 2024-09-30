<template>
  <div class="flex">
    <SelectField
      fieldClassName="language"
      field="language"
      filter
      inputClassName="languages-dropdown"
      v-model="language"
      :options="ttsLanguages"
      optionLabel="label"
      optionValue="value"
      v-tooltip="'The language of Text to Speech'"
      @before-show="handleSelectBeforeShow"
      @before-hide="handleSelectBeforeHide"
    />
    <TextInput
      placeholder="Text to Speech"
      @keydown.stop="doThis"
      @keyup.stop="doThis"
      @keypress.stop="doThis"
      @keyup.enter="handleKeyEnter"
      v-model="text"
      v-tooltip="'Type the Text To Speech and press Enter to speak'"
    />
    <ButtonGroup>
      <Button
        @click="sayText"
        :disabled="text.length === 0"
        icon="pi pi-play-circle"
        text
        rounded
        aria-label="Speak"
        v-tooltip="'Speak'"
      />
      <TextToSpeechButton />
    </ButtonGroup>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import TextInput from "primevue/inputtext";
import { ref } from "vue";
import ButtonGroup from "primevue/buttongroup";

import { ttsLanguages } from "@/features/settings/config";
import SelectField from "@/ui/SelectField.vue";
import TextToSpeechButton from "@/features/settings/components/TextToSpeechButton.vue";

const store = useSettingsStore();

const language = ref("en");
const text = ref("");

const doThis = () => {};
const handleSelectBeforeShow = () => {
  store.inhibitKeyHandling = true;
};

const handleSelectBeforeHide = () => {
  store.inhibitKeyHandling = false;
};

const sayText = async () => {
  const value = text.value;
  if (value && value.length) {
    await store.speakText(value, language.value);
  }
};
const handleKeyEnter = async () => {
  const value = text.value;
  if (value && value.length > 0) {
    text.value = "";
    await store.speakText(value, language.value);
  }
};
</script>

<style scoped lang="scss">
.flex {
  display: flex;
  align-items: center;
  opacity: 0.6;
}
.tag {
  cursor: pointer;
}

input {
  min-width: 50px;
  margin: 0 0.5rem;

  @media (min-width: 576px) {
    width: 100px;
  }
  @media (min-width: 768px) {
    width: 100px;
  }
  @media (min-width: 992px) {
    width: 120px;
  }
  @media (min-width: 1200px) {
    width: 140px;
  }
}
.language {
  width: 40px;

  @media (min-width: 576px) {
    width: 60px;
  }
  @media (min-width: 768px) {
    width: 80px;
  }
  @media (min-width: 992px) {
    width: 100px;
    :deep(.p-select-label) {
      padding: 0.15rem 0.4rem;

      @media (min-width: 576px) {
        padding: 0.25rem 0.7rem;
      }

      @media (min-width: 768px) {
        padding: 0.3rem 0.7rem;
      }

      @media (min-width: 1200px) {
        padding: 0.4rem 0.7rem;
      }
    }
  }
}
</style>
