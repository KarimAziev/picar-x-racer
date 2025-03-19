<template>
  <Dialog
    v-if="selectedItem"
    :header="selectedItem.name"
    content-class="sm:min-w-[600px] md:min-w-[700px] lg:min-w-[1000px] xl:min-[1200px] h-[85vh]"
    v-model:visible="visible"
    dismissableMask
    modal
    @show="handleShow"
    @after-hide="handleHide"
  >
    <div class="flex flex-col w-full justify-between h-full">
      <div class="flex flex-nowrap justify-between w-full text-center my-auto">
        <div class="flex-1">
          <button
            @click="handlePrevImagePreview"
            class="w-full h-full text-left hover:text-robo-color-primary disabled:hover:bg-transparent disabled:opacity-60 px-4"
          >
            <i class="pi pi-chevron-left" />
          </button>
        </div>
        <video
          ref="videoRef"
          controls
          autoplay
          :poster="selectedPosterURL || undefined"
          class="h-auto max-w-[80%]"
        >
          <source :src="selectedItemURL" type="video/mp4" />
          Your browser does not support the video tag.
        </video>

        <div class="flex-1">
          <button
            @click="handleNextImagePreview"
            class="w-full h-full text-right hover:text-robo-color-primary disabled:hover:bg-transparent disabled:opacity-60 px-4"
          >
            <i class="pi pi-chevron-right" />
          </button>
        </div>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import type { GroupedFile } from "@/features/files/interface";
import { computed, useTemplateRef, nextTick, onBeforeUnmount } from "vue";
import Dialog from "primevue/dialog";
import { cycleValue } from "@/util/cycleValue";
import { useKeyboardHandlers } from "@/composables/useKeyboardHandlers";

const props = defineProps<{
  items: GroupedFile[];
  makeVideoPreviewURL: (path: GroupedFile["path"]) => string;
  makeVideoURL: (path: GroupedFile["path"]) => string;
}>();

const visible = defineModel<boolean>("visible", { required: true });
const selectedItem = defineModel<GroupedFile>("selectedItem");
const emit = defineEmits(["show", "after-hide"]);

const videoRef = useTemplateRef("videoRef");

const handleShow = () => {
  addKeyEventListeners();
  emit("show");
};
const handleHide = () => {
  removeKeyEventListeners();
  emit("after-hide");
};
const selectedItemURL = computed(() =>
  selectedItem.value
    ? props.makeVideoURL(selectedItem.value.path)
    : selectedItem.value,
);

const selectedPosterURL = computed(() =>
  selectedItem.value
    ? props.makeVideoPreviewURL(selectedItem.value.path)
    : null,
);

const handleCycle = (direction: number) => {
  videoRef.value?.pause();
  const nextImg = cycleValue(
    ({ path }) => path === selectedItem.value?.path,
    props.items,
    direction,
  );
  selectedItem.value = nextImg;
  nextTick(() => {
    if (videoRef.value) {
      videoRef.value.load();
      videoRef.value.play();
    }
  });
};

const handleNextImagePreview = () => {
  handleCycle(1);
};

const handlePrevImagePreview = () => {
  handleCycle(-1);
};

const { addKeyEventListeners, removeKeyEventListeners } = useKeyboardHandlers({
  ArrowLeft: () => {
    if (videoRef.value?.paused) {
      handlePrevImagePreview();
    }
  },
  ArrowRight: () => {
    if (videoRef.value?.paused) {
      handleNextImagePreview();
    }
  },
});

onBeforeUnmount(removeKeyEventListeners);
</script>
