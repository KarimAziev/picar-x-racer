<template>
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
      <ResizableImg
        :minHeight="minHeight"
        :minWidth="minWidth"
        :maxHeight="maxHeight"
        :maxWidth="adjustedMaxWidth"
        :alt="selectedImage?.alt"
        :src="selectedImage?.src"
      />

      <div class="flex-1">
        <button
          @click="handleNextImagePreview"
          class="w-full h-full text-right hover:text-robo-color-primary disabled:hover:bg-transparent disabled:opacity-60 px-4"
        >
          <i class="pi pi-chevron-right" />
        </button>
      </div>
    </div>
    <div class="flex justify-center mt-4">
      <span
        v-for="(_, index) in images"
        :key="index"
        @click="handleUpdateActiveIndex(index)"
        class="w-3 h-3 mx-1 cursor-pointer rounded-full transition-all duration-300"
        :class="{
          'bg-robo-color-primary scale-125': index === activeIndex,
          'bg-gray-400 hover:bg-gray-500': index !== activeIndex,
        }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from "vue";

import { isNumber } from "@/util/guards";
import ResizableImg from "@/ui/ResizableImg.vue";
import { useKeyboardHandlers } from "@/composables/useKeyboardHandlers";

export interface ImageItem {
  title?: string;
  alt?: string;
  src: string;
}

const activeIndex = defineModel<number>("activeIndex", { required: true });
const emit = defineEmits(["update:activeIndex"]);

const props = defineProps<{
  images: ImageItem[];
  numVisible?: number;
  minWidth: number;
  maxWidth: number;
  minHeight: number;
  maxHeight: number;
}>();

const btnWidth = 80;

const selectedImage = computed(() => props.images[activeIndex.value]);

const adjustedMaxWidth = computed(() => props.maxWidth - btnWidth * 2);

const handleUpdateActiveIndex = (value: number) => {
  activeIndex.value = value;
  emit("update:activeIndex", value);
};

const handleNextImagePreview = () => {
  if (isNumber(activeIndex.value)) {
    activeIndex.value =
      activeIndex.value === props.images.length - 1
        ? props.images.length - 1
        : activeIndex.value + 1;
  }
};

const handlePrevImagePreview = () => {
  if (isNumber(activeIndex.value)) {
    handleUpdateActiveIndex(
      activeIndex.value === 0 ? 0 : activeIndex.value - 1,
    );
  }
};

const { addKeyEventListeners, removeKeyEventListeners } = useKeyboardHandlers({
  ArrowLeft: handlePrevImagePreview,
  ArrowRight: handleNextImagePreview,
});

onMounted(addKeyEventListeners);
onBeforeUnmount(removeKeyEventListeners);
</script>
