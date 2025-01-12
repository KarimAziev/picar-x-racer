<template>
  <div
    class="xl:max-w-[300] lg:max-w-[270px] md:max-w-[200px] flex flex-wrap items-center gap-2"
  >
    <SelectField
      fieldClassName="w-[70px]"
      field="language"
      filter
      v-model="language"
      :loading="langsLoading"
      :options="ttsOptions"
      optionLabel="label"
      optionValue="value"
      tooltip="The current language of text to speech (%s)"
      @before-show="handleSelectBeforeShow"
      @before-hide="handleSelectBeforeHide"
      @hide="focusToKeyboardHandler"
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
import { ref, watch, computed, onMounted } from "vue";
import TextInput from "primevue/inputtext";
import { useSettingsStore, useTTSStore } from "@/features/settings/stores";

import SelectField from "@/ui/SelectField.vue";

import { useInputHistory } from "@/composables/useInputHistory";
import { focusToKeyboardHandler } from "@/features/controller/util";

defineProps<{ class?: string }>();

const settingsStore = useSettingsStore();
const ttsStore = useTTSStore();

const langsLoading = computed(() => !!ttsStore.loading);

const ttsOptions = computed(() => {
  if (
    !settingsStore.data.tts.allowed_languages ||
    !settingsStore.data.tts.allowed_languages.length
  ) {
    return ttsStore.data;
  }
  const hashLangs = new Map(
    ttsStore.data.map(({ value, label }) => [value, label]),
  );
  return settingsStore.data.tts.allowed_languages.map((code) => ({
    value: code,
    label: hashLangs.get(code) || code,
  }));
});

const language = ref(settingsStore.data.tts.default_tts_language);

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
  settingsStore.inhibitKeyHandling = true;
};

const handleSelectBeforeHide = () => {
  settingsStore.inhibitKeyHandling = false;
};

const handleKeyEnter = async () => {
  const value = inputRef.value;
  if (value && value.length > 0) {
    inputRef.value = "";
    inputHistory.value?.push(value);
    await settingsStore.speakText(value, language.value);
  }
};

watch(
  () => settingsStore.data.tts.default_tts_language,
  (newValue) => {
    language.value = newValue;
  },
);

onMounted(ttsStore.fetchLanguagesOnce);
</script>
