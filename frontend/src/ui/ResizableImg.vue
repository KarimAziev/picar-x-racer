<template>
  <span
    ref="resizableWrapper"
    :class="wrapperClassName"
    class="relative inline-block w-full select-none overflow-visible"
  >
    <ProgressSpinner
      v-bind="otherAttrs"
      class="auto my-auto text-center"
      v-if="imgLoading"
      :style="minWidth ? `min-width: ${minWidth}px;` : undefined"
    />
    <img
      ref="imgRef"
      :src="src"
      class="my-auto text-center select-none h-auto w-full auto block transition-opacity cursor-pointer"
      @load="handleImageOnLoad"
      @error="handleImageOnLoad"
      :class="imgClass"
      v-bind="otherAttrs"
    />
    <Resizers v-model="size" />
  </span>
</template>

<script setup lang="ts">
import { ref, useAttrs, computed, watch, nextTick, useTemplateRef } from "vue";
import ProgressSpinner from "primevue/progressspinner";
import { useElementSize } from "@/composables/useElementSize";
import Resizers from "@/ui/Resizers.vue";
import { isNumber } from "@/util/guards";
import { roundToOneDecimalPlace, resizeToFit } from "@/util/number";

const imgLoading = ref(true);
const otherAttrs = useAttrs();

const imgRef = useTemplateRef("imgRef");
const resizableWrapper = ref<HTMLElement | null>(null);
const aspectRatio = ref<number>();
const size = ref({ width: 0, height: 0 });

const imgSize = useElementSize(imgRef);
const props = defineProps<{
  className?: string;
  wrapperClass?: string;
  src: string;
  minWidth: number;
  maxWidth: number;
  minHeight: number;
  maxHeight: number;
}>();

const wrapperClassName = computed(() =>
  imgLoading.value ? { block: true } : {},
);

watch(
  [() => size.value.width, () => size.value.height],
  ([newWidth, newHeight]) => {
    if (imgLoading.value || !isNumber(newHeight) || !isNumber(newWidth)) {
      return;
    }
    if (!resizableWrapper.value) {
      return;
    }
    resizableWrapper.value.style.width = `${newWidth}px`;
    /**
     * resizableWrapper.value.style.height = `${newHeight}px`;
     */
  },
);

const imgClass = computed(() =>
  props.className
    ? { [props.className]: props.className, loading: imgLoading.value }
    : {
        loading: imgLoading.value,
      },
);

const onImageLoad = () => {
  aspectRatio.value = roundToOneDecimalPlace(imgSize.width / imgSize.height);
  const [maxWidth, maxHeight] = resizeToFit(
    imgSize.width,
    imgSize.height,
    props.maxWidth,
    props.maxHeight,
  );

  size.value.width = maxWidth;
  size.value.height = maxHeight;
  imgLoading.value = false;
};

watch(
  [() => props.maxWidth, () => props.maxHeight],
  ([wndWidth, wndHeight]) => {
    if (!imgLoading.value) {
      const [maxWidth, maxHeight] = resizeToFit(
        imgSize.width,
        imgSize.height,
        wndWidth,
        wndHeight,
      );
      size.value.width = maxWidth;
      size.value.height = maxHeight;
    }
  },
);

const handleImageOnLoad = () => {
  nextTick(() => {
    onImageLoad();
  });
};
</script>

<style scoped lang="scss">
.loading {
  opacity: 0;
  position: absolute;
  left: 100000px;
}
</style>
