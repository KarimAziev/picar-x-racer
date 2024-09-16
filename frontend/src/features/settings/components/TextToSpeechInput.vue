<template>
  <div class="flex">
    <SelectField
      fieldClassName="language"
      field="language"
      filter
      v-model="language"
      :options="ttsLanguages"
      :simpleOptions="true"
      v-tooltip="'The language of Text to Speech'"
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
        raised
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
.language {
  width: 40px;
}
input {
  min-width: 80px;
}
@media (min-width: 768px) {
  input {
    min-width: 120px;
  }
  .language {
    width: 100px;
  }
}

@media (min-width: 1200px) {
  input {
    min-width: 150px;
  }
}
</style>
