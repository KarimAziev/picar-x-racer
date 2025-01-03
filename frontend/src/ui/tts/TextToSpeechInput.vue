<template>
  <div
    class="xl:max-w-[300] lg:max-w-[270px] md:max-w-[200px] flex flex-wrap items-center gap-2"
  >
    <SelectField
      fieldClassName="w-[70px]"
      field="language"
      filter
      v-model="language"
      :options="ttsLanguages"
      optionLabel="label"
      optionValue="value"
      tooltip="The current language of text to speech (%s)"
      @before-show="handleSelectBeforeShow"
      @before-hide="handleSelectBeforeHide"
    />
    <div class="flex items-center">
      <TextInput
        autocomplete="off"
        placeholder="Speak"
        id="tts-text"
        @keyup.stop="handleKeyUp"
        @keyup.enter="handleKeyEnter"
        v-model="inputRef"
        v-tooltip="textInputTooltip"
      />
      <Button
        @click="handleKeyEnter"
        :disabled="!inputRef || inputRef.length === 0"
        icon="pi pi-play-circle"
        text
        aria-label="Speak"
        v-tooltip="tooltipButtonText"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import TextInput from "primevue/inputtext";
import { useSettingsStore } from "@/features/settings/stores";

import { ttsLanguages } from "@/features/settings/config";
import SelectField from "@/ui/SelectField.vue";

import { useInputHistory } from "@/composables/useInputHistory";

defineProps<{ class?: string }>();

const store = useSettingsStore();
const language = ref(store.data.tts.default_tts_language);

const { inputHistory, inputRef, handleKeyUp } = useInputHistory("");

const isEnabled = computed(
  () => inputRef.value && !!inputRef.value.trim().length,
);

const textInputTooltip = computed(() =>
  isEnabled.value
    ? `Press 'Enter' to speak: '${inputRef.value}'`
    : "Type the text to speech and press 'Enter' to speak",
);

const tooltipButtonText = computed(() =>
  isEnabled.value ? "Click to speak the text" : "Type a text to speak",
);

const handleSelectBeforeShow = () => {
  store.inhibitKeyHandling = true;
};

const handleSelectBeforeHide = () => {
  store.inhibitKeyHandling = false;
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
  () => store.data.tts.default_tts_language,
  (newValue) => {
    language.value = newValue;
  },
);
</script>
