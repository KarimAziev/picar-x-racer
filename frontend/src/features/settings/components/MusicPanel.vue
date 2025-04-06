<template>
  <FilesTree :store="store" :uploadURL="uploadURL">
    <template #headerButtons>
      <div class="flex-auto flex items-center justify-between">
        <Button
          variant="outlined"
          type="button"
          label="Reorder"
          @click="handleOpenPopup"
        ></Button>
        <SelectField
          field="settings.music.mode"
          label="Default Mode"
          class="w-30 self-start"
          :options="musicModes"
          v-model="musicStore.player.mode"
          @update:model-value="handleUpdateMusicMode"
        />
      </div>
    </template>
  </FilesTree>
  <Dialog
    header="Drag the row to reorder"
    maximizable
    v-model:visible="reorderPopupOpen"
    @show="
      () => {
        popupStore.isEscapable = false;
      }
    "
    @after-hide="
      () => {
        popupStore.isEscapable = true;
      }
    "
  >
    <Music />
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import FilesTree from "@/features/files/components/FilesTree.vue";
import { useMusicStore } from "@/features/music";
import { useMusicFileStore } from "@/features/files/stores";
import { makeUploadURL } from "@/features/files/api";

const popupStore = usePopupStore();
import Music from "@/features/settings/components/music/Music.vue";
import { usePopupStore } from "@/features/settings/stores";
import { MusicMode } from "@/features/music/store";
import { startCase } from "@/util/str";
import SelectField from "@/ui/SelectField.vue";

const reorderPopupOpen = ref(false);

const musicModes = Object.values(MusicMode).map((value) => ({
  value,
  label: startCase(value),
}));

const store = useMusicFileStore();
const musicStore = useMusicStore();

const handleOpenPopup = () => {
  musicStore.fetchData();
  reorderPopupOpen.value = true;
};

const handleUpdateMusicMode = async (mode: MusicMode) => {
  await musicStore.updateMode(mode);
};

const uploadURL = computed(() => makeUploadURL(store.mediaType));
</script>
