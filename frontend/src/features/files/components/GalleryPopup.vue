<template>
  <Dialog
    :content-class="
      isMaximized
        ? 'w-full h-full'
        : 'sm:w-[600px] md:w-[700px] lg:w-[1000px] xl:w-[1200px] h-[85vh]'
    "
    :header="imageHeader"
    maximizable
    v-model:visible="galleryPopupVisible"
    dismissableMask
    modal
    @maximize="handleMaximize"
    @unmaximize="handleUnmaximize"
    @after-hide="afterHide"
  >
    <Gallery
      v-model:activeIndex="selectedImageIdx"
      :getItemURL="getItemURL"
      :images="images"
      :numVisible="10"
      :maxWidth="maxWidth"
      :minWidth="minWidth"
      :maxHeight="maxHeight"
      :minHeight="minHeight"
    ></Gallery>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import Gallery from "@/ui/Gallery.vue";
import type { Props as GalleryProps } from "@/ui/Gallery.vue";
import { takePercentage } from "@/util/number";
import { isNumber } from "@/util/guards";
import { useWindowSize } from "@/composables/useWindowSize";

export interface Props
  extends Pick<
    GalleryProps,
    "images" | "getItemURL" | "altProp" | "titleProp"
  > {}

const props = defineProps<Props>();

const emit = defineEmits(["after-hide"]);

const selectedImageIdx = defineModel<number>("selectedImageIdx", {
  required: true,
});
const galleryPopupVisible = defineModel<boolean>("galleryPopupVisible", {
  required: true,
});

const isMaximized = ref(false);

const wndSize = useWindowSize();

const imageHeader = computed(() => {
  const result = isNumber(selectedImageIdx.value)
    ? props.images[selectedImageIdx.value]?.name
    : undefined;
  return result;
});

const minWidth = computed(() => Math.min(640, wndSize.width.value));

const maxWidth = computed(() =>
  Math.max(minWidth.value, takePercentage(wndSize.width.value, 90)),
);
const minHeight = computed(() => takePercentage(wndSize.height.value, 75));

const maxHeight = computed(() => minHeight.value);

const handleMaximize = () => {
  isMaximized.value = true;
};

const handleUnmaximize = () => {
  isMaximized.value = false;
};

const afterHide = () => {
  emit("after-hide");
};
</script>
