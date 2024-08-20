<template>
  <Panel>
    <div class="wrapper">
      <div class="field">
        <label>Text to speech</label>
        <Textarea
          v-tooltip="'Type the text to speech'"
          @blur="autoSaveSettings"
          v-model="store.settings.default_text"
          rows="5"
          cols="30"
        />
      </div>
      <Divider />
      <div class="field">
        <label for="default_sound">Default Sound</label>
        <Select
          @blur="autoSaveSettings"
          class="select"
          v-model="store.settings.default_sound"
          :options="soundStore.data"
        />
      </div>
      <Sounds />
      <Divider />
      <div class="field">
        <label for="default_music">Default Music</label>
        <Select
          @blur="autoSaveSettings"
          class="select"
          v-model="store.settings.default_music"
          :options="musicStore.data"
        />
      </div>
      <Music />
      <Panel header="Photos" toggleable>
        <Images />
      </Panel>
    </div>
  </Panel>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import Divider from "primevue/divider";

import {
  useSettingsStore,
  useMusicStore,
  useSoundStore,
} from "@/features/settings/stores";
import Panel from "primevue/panel";
import Select from "primevue/select";
import Textarea from "primevue/textarea";

import Sounds from "@/features/settings/components/Sounds.vue";
import Music from "@/features/settings/components/Music.vue";
import Images from "@/features/settings/components/Images.vue";

const store = useSettingsStore();
const musicStore = useMusicStore();
const soundStore = useSoundStore();

function autoSaveSettings() {
  store.saveSettings();
}

onMounted(() => {
  store.fetchSettings();
  musicStore.fetchData();
  soundStore.fetchData();
});
</script>

<style scoped lang="scss">
@import "/src/assets/scss/variables.scss";

.wrapper {
  min-width: 820px;
  max-width: 1200px;
  margin: auto;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  justify-items: center;
}

.field {
  display: flex;
  flex-direction: column;
  margin: 1rem 0;
}
.select {
  width: 200px;
}
</style>
