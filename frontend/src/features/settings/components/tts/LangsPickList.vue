<template>
  <div class="card">
    <PickList
      @update:model-value="handleUpdate"
      v-model="languages"
      dataKey="value"
      :pt="{ pcListbox: { emptyMessage: 'hidden' } }"
    >
      <template #sourceheader> Allowed languages </template>
      <template #targetheader> Excluded languages </template>
      <template #option="{ option }">
        {{ option.label }}
      </template>
    </PickList>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useSettingsStore, useTTSStore } from "@/features/settings/stores";
import type { LanguageOption } from "@/features/settings/stores/tts";

const settingsStore = useSettingsStore();
const ttsStore = useTTSStore();

export type MultiDimensionValue = [LanguageOption[], LanguageOption[]];

const hashLangs = computed(
  () => new Map(ttsStore.data.map(({ value, label }) => [value, label])),
);

const getInitialValue = () => {
  const codes = new Set(settingsStore.data.tts.allowed_languages || []);

  if (
    !settingsStore.data.tts.allowed_languages ||
    !settingsStore.data.tts.allowed_languages.length
  ) {
    return [ttsStore.data, []] as MultiDimensionValue;
  }

  const allowedLanguages = settingsStore.data.tts.allowed_languages.map(
    (code) => ({ value: code, label: hashLangs.value.get(code) || code }),
  );
  const exludedLanguages = ttsStore.data.filter(
    ({ value }) => !codes.has(value),
  );
  return [allowedLanguages, exludedLanguages];
};

const languages = ref(getInitialValue());

const handleUpdate = (newValue: any[][]) => {
  const pair = newValue as MultiDimensionValue;
  const [allowed, excluded] = pair;
  if (!allowed.length) {
    const allowedHash = new Set(
      settingsStore.data.tts.texts
        .map(({ language }) => language)
        .concat([settingsStore.data.tts.default_tts_language]),
    );
    const allowedOptions = Array.from(allowedHash).map((key) => ({
      value: key,
      label: hashLangs.value.get(key) || key,
    }));

    const excludedOptions = excluded.filter(
      ({ value }) => !allowedHash.has(value),
    );

    pair[0] = allowedOptions;
    pair[1] = excludedOptions;
  }

  settingsStore.data.tts.allowed_languages = pair[0].map(({ value }) => value);
};
</script>
