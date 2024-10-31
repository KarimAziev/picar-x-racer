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
      id="tts-text"
      @keydown.stop="doThis"
      @keyup.stop="handleKeyUp"
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
import { ref, watch } from "vue";
import TextInput from "primevue/inputtext";
import { useSettingsStore } from "@/features/settings/stores";
import ButtonGroup from "primevue/buttongroup";

import { ttsLanguages } from "@/features/settings/config";
import SelectField from "@/ui/SelectField.vue";
import TextToSpeechButton from "@/features/settings/components/TextToSpeechButton.vue";
import { isNumber } from "@/util/guards";
import { useKeyboardHandlers } from "@/composables/useKeyboardHandlers";

const store = useSettingsStore();
const inputHistory = ref<string[]>([]);
const currHistoryIdx = ref(0);

const language = ref(store.settings.default_tts_language);
const text = ref("");

const doThis = () => {};
const handleSelectBeforeShow = () => {
  store.inhibitKeyHandling = true;
};

const handleSelectBeforeHide = () => {
  store.inhibitKeyHandling = false;
};

const getNextOrPrevHistoryText = (n: number) => {
  if (!isNumber(currHistoryIdx.value) || !inputHistory.value?.length) {
    return;
  }
  const maxIdx = inputHistory.value.length - 1;
  const incIdx = currHistoryIdx.value + n;
  const newIdx =
    incIdx >= 0 && incIdx <= maxIdx ? incIdx : n > 0 ? 0 : Math.abs(maxIdx);
  const newText = inputHistory.value[newIdx];
  if (newText) {
    text.value = newText;
    currHistoryIdx.value = newIdx;
  }
};

const setNextHistoryText = () => {
  getNextOrPrevHistoryText(1);
};

const setPrevHistoryText = () => {
  getNextOrPrevHistoryText(-1);
};

const inputKeyHandlers: { [key: string]: Function } = {
  ArrowUp: setPrevHistoryText,
  ArrowDown: setNextHistoryText,
};

const { handleKeyUp } = useKeyboardHandlers(inputKeyHandlers);

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
    inputHistory.value?.push(value);
    await store.speakText(value, language.value);
  }
};

watch(
  () => store.settings.default_tts_language,
  (newValue) => {
    language.value = newValue;
  },
);
</script>

<style scoped lang="scss">
.flex {
  display: flex;
  align-items: center;
  opacity: 0.6;

  @media screen and (max-width: 992px) {
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
  }

  @media screen and (max-width: 480px) and (orientation: landscape) {
  }

  @media (min-width: 1200px) {
  }
}
.tag {
  cursor: pointer;
}

input {
  min-width: 50px;

  @media (min-width: 992px) {
    margin: 0 0.5rem;
  }

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
