<template>
  <Panel header="Text to Speech" toggleable collapsed>
    <DataTable />
    <div class="pair">
      <SelectField
        fieldClassName="language"
        field="default_language"
        v-model="store.settings.default_language"
        :options="ttsLanguages"
        :simpleOptions="true"
      />
      <Textarea
        id="default_text"
        v-tooltip="'Type the text to speech'"
        v-model="store.settings.default_text"
      />
    </div>
  </Panel>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/features/settings/stores";
import Panel from "primevue/panel";
import Textarea from "primevue/textarea";
import { computed } from "vue";

import { ttsLanguages } from "@/features/settings/config";
import SelectField from "@/ui/SelectField.vue";

const store = useSettingsStore();
</script>

<style scoped lang="scss">
.pair {
  display: flex;
  align-items: center;
  .language {
    width: 100px;
  }
  .field {
    flex: auto;
  }
}
.field {
  display: flex;

  margin: 1rem 0;
  .input-number,
  textarea,
  input {
    font-size: 10px;
  }
  @media (min-width: 640px) {
    .input-number,
    textarea,
    input {
      font-size: 1rem;
    }
  }
}
</style>
