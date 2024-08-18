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
          :options="store.sounds"
        />
      </div>
      <FilesPanel
        :fetch-data="store.fetchSounds"
        toggleable
        header="Sounds"
        url="/api/upload/sound"
        :files="store.sounds"
        :download-file="(file) => store.downloadFile('sound', file)"
        :remove-file="store.removeSoundFile"
      >
      </FilesPanel>
      <Divider />
      <div class="field">
        <label for="default_music">Default Music</label>
        <Select
          @blur="autoSaveSettings"
          class="select"
          v-model="store.settings.default_music"
          :options="store.music"
        />
      </div>
      <FilesPanel
        toggleable
        :fetch-data="store.fetchMusic"
        header="Music"
        url="/api/upload/music"
        :files="store.music"
        :download-file="(file) => store.downloadFile('music', file)"
        :remove-file="store.removeMusicFile"
      />
      <Panel header="Photos" toggleable>
        <FileList
          :fetch-data="store.fetchImages"
          :files="store.images"
          :download-file="(file) => store.downloadFile('image', file)"
          :remove-file="store.removeImageFile"
        />
      </Panel>
    </div>
  </Panel>
</template>

<script setup lang="ts">
import Divider from "primevue/divider";

import Panel from "primevue/panel";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { onMounted } from "vue";
import { useSettingsStore } from "@/features/settings/store";

import FilesPanel from "@/features/settings/components/FilesPanel.vue";
import FileList from "@/features/settings/components/FileList.vue";

const store = useSettingsStore();
function autoSaveSettings() {
  store.saveSettings();
}
onMounted(() => {
  store.fetchSettings();
  store.fetchSounds();
  store.fetchMusic();
  store.fetchImages();
});
</script>

<style scoped lang="scss">
@import "/src/assets/scss/variables.scss";

.title {
  text-align: center;
}
.logo {
  width: 100px;
  fill: var(--link-color);
}
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
