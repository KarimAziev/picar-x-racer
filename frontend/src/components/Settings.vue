<template>
  <div class="wrapper">
    <IconLogo class="logo" />
    <Panel header="Settings">
      <div class="field">
        <label>Text to speech</label>
        <Textarea
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

      <Panel toggleable header="Sounds">
        <FileUpload
          :auto="true"
          mode="basic"
          name="file"
          @upload="onSoundUpload($event)"
          url="/api/upload/sound"
          :multiple="false"
          accept="audio/*"
        >
        </FileUpload>
        <div v-if="!!store.sounds?.length" class="file-list">
          <ul class="files">
            <li v-for="sound in store.sounds" :key="sound" class="filerow">
              <span class="filename">{{ sound }}</span>

              <Button
                severity="secondary"
                outlined
                icon="pi pi-download"
                @click="store.downloadFile('sound', sound)"
              >
              </Button>
              <Button
                icon="pi pi-times"
                text
                severity="danger"
                @click="store.removeSoundFile(sound)"
              ></Button>
            </li>
          </ul>
        </div>
      </Panel>
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
      <Panel toggleable header="Music">
        <FileUpload
          :auto="true"
          mode="basic"
          name="file"
          @upload="onMusicUpload($event)"
          url="/api/upload/music"
          :multiple="false"
          accept="audio/*"
        >
        </FileUpload>
        <div v-if="!!store.music?.length" class="file-list">
          <ul class="files">
            <li v-for="track in store.music" :key="track" class="filerow">
              <span class="filename">{{ track }}</span>
              <Button
                severity="secondary"
                outlined
                icon="pi pi-download"
                @click="store.downloadFile('music', track)"
              >
              </Button>
              <Button
                severity="danger"
                text
                icon="pi pi-times"
                @click="store.removeMusicFile(track)"
              ></Button>
            </li>
          </ul>
        </div>
      </Panel>
      <Panel toggleable header="Photos" collapsed>
        <div v-if="!!store.images?.length" class="file-list">
          <ul class="files">
            <li v-for="image in store.images" :key="image" class="filerow">
              <span class="filename">{{ image }}</span>
              <Button
                outlined
                severity="secondary"
                icon="pi pi-download"
                @click="store.downloadFile('image', image)"
              >
              </Button>
              <Button
                severity="danger"
                text
                icon="pi pi-times"
                @click="store.removeImageFile(image)"
              ></Button>
            </li>
          </ul>
        </div>
      </Panel>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import Button from "primevue/button";
import Divider from "primevue/divider";
import { default as FileUpload } from "primevue/fileupload";
import Panel from "primevue/panel";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { onMounted } from "vue";
import { useSettingsStore } from "@/stores/settings";
import { useToast } from "primevue/usetoast";
import { FileUploadUploadEvent } from "primevue/fileupload";
import IconLogo from "@/components/icons/IconLogo.vue";

const toast = useToast();

const onSoundUpload = (_event: FileUploadUploadEvent) => {
  store.fetchSounds();
  toast.add({
    severity: "info",
    summary: "Success",
    detail: "File Uploaded",
    life: 3000,
  });
};
const onMusicUpload = (_event: FileUploadUploadEvent) => {
  store.fetchMusic();
  toast.add({
    severity: "info",
    summary: "Success",
    detail: "File Uploaded",
    life: 3000,
  });
};
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
  display: flex;
  padding: 5rem;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  justify-items: center;
}

.field {
  display: flex;
  flex-direction: column;
}
.select {
  width: 200px;
}

.files {
  display: flex;
  list-style: none;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
}
.filerow {
  display: flex;
  gap: 5px;
  justify-content: space-between;
}
.filename {
  width: 500px;
}
</style>
