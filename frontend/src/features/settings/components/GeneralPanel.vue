<template>
  <ScrollPanel class="wrapper">
    <Panel header="Appearance">
      <SwitchSettings />
    </Panel>
    <Panel header="Text to Speech">
      <div class="field">
        <label for="default_language">Language</label>
        <Select
          id="languages"
          v-model="store.settings.default_language"
          :options="ttsLanguages"
        />
      </div>
      <div class="field">
        <label for="default_text">Text</label>
        <Textarea
          v-tooltip="'Type the text to speech'"
          v-model="store.settings.default_text"
        />
      </div>
    </Panel>
    <div class="field">
      <label for="video_feed_url">Video URL</label>
      <Select
        id="video_feed_url"
        class="select"
        v-model="store.settings.video_feed_url"
        optionLabel="label"
        optionValue="value"
        :options="videoFeedOptions"
      />
    </div>
    <Divider />
    <div class="field">
      <label for="default_sound">Default Sound</label>
      <Select
        id="default_sound"
        class="select"
        v-model="store.settings.default_sound"
        :options="allSounds"
      />
    </div>
    <Sounds />
    <Divider />
    <div class="field">
      <label for="default_music">Default Music</label>
      <Select
        id="default_music"
        class="select"
        v-model="store.settings.default_music"
        :options="allMusic"
      />
    </div>
    <Music />
    <Panel header="Photos" toggleable>
      <Images />
    </Panel>
  </ScrollPanel>
</template>

<script setup lang="ts">
import { computed } from "vue";
import Divider from "primevue/divider";

import {
  useSettingsStore,
  useMusicStore,
  useSoundStore,
} from "@/features/settings/stores";
import Panel from "primevue/panel";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import ScrollPanel from "primevue/scrollpanel";

import Sounds from "@/features/settings/components/Sounds.vue";
import Music from "@/features/settings/components/Music.vue";
import Images from "@/features/settings/components/Images.vue";
import { VideoFeedURL } from "@/features/settings/enums";
import SwitchSettings from "@/features/settings/components/SwitchSettings.vue";
import { ttsLanguages } from "@/features/settings/config";

const videoFeedOptions = Object.entries(VideoFeedURL).map(([key, value]) => ({
  value,
  label: key.toUpperCase(),
}));

const store = useSettingsStore();
const musicStore = useMusicStore();
const soundStore = useSoundStore();

const allSounds = computed(() => [
  ...soundStore.data,
  ...soundStore.defaultData,
]);
const allMusic = computed(() => [
  ...musicStore.data,
  ...musicStore.defaultData,
]);
</script>

<style scoped lang="scss">
.wrapper {
  min-width: 620px;
  max-width: 1200px;
  height: 800px;
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
