<template>
  <div class="container flex align-items-center gap-5" :class="class">
    <SelectField
      fieldClassName="language opacity-hover"
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
    <div class="flex textinput">
      <TextInput
        class="opacity-hover"
        autocomplete="off"
        placeholder="Speak"
        id="tts-text"
        @keyup.stop="handleKeyUp"
        @keyup.enter="handleKeyEnter"
        v-model="inputRef"
        v-tooltip="'Type the Text To Speech and press Enter to speak'"
      />

      <Button
        class="opacity-hover"
        @click="sayText"
        :disabled="!inputRef || inputRef.length === 0"
        icon="pi pi-play-circle"
        text
        aria-label="Speak"
        v-tooltip="'Speak'"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import TextInput from "primevue/inputtext";
import { useSettingsStore } from "@/features/settings/stores";

import { ttsLanguages } from "@/features/settings/config";
import SelectField from "@/ui/SelectField.vue";

import { useInputHistory } from "@/composables/useInputHistory";

defineProps<{ class?: string }>();

const store = useSettingsStore();

const language = ref(store.data.default_tts_language);

const { inputHistory, inputRef, handleKeyUp } = useInputHistory("");

const handleSelectBeforeShow = () => {
  store.inhibitKeyHandling = true;
};

const handleSelectBeforeHide = () => {
  store.inhibitKeyHandling = false;
};

const sayText = async () => {
  const value = inputRef.value;
  if (value && value.length) {
    await store.speakText(value, language.value);
  }
};
const handleKeyEnter = async () => {
  const value = inputRef.value;
  if (value && value.length > 0) {
    inputRef.value = "";
    inputHistory.value?.push(value);
    await store.speakText(value, language.value);
  }
};

watch(
  () => store.data.default_tts_language,
  (newValue) => {
    language.value = newValue;
  },
);
</script>

<style scoped lang="scss">
.container {
  @media screen and (max-width: 992px) {
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
    gap: 0;
  }
}
input {
  width: 50px;
  height: 30px;

  @media (min-width: 576px) {
    width: 120px;
  }

  @media (min-width: 1200px) {
    height: 40px;
    width: 140px;
  }
}
.language {
  width: 50px;
  @media (min-width: 576px) {
    width: 60px;
  }
  @media (min-width: 768px) {
    width: 80px;
  }
  @media (min-width: 992px) {
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
