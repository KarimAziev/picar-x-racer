<template>
  <figure
    class="relative h-auto inline-flex flex-col justify-center items-center"
  >
    <ProgressSpinner
      :style="`width: 50%;`"
      class="auto my-auto text-center"
      v-if="imgLoading"
    />

    <img
      v-if="!failed && width"
      class="auto transition-opacity cursor-pointer"
      @load="handleImageOnLoad"
      @error="handleOnError"
      :class="imgClass"
      :style="`width: ${width}px;`"
      v-bind="otherAttrs"
    />
    <img
      v-else-if="!failed && !width"
      class="auto transition-opacity cursor-pointer"
      @load="handleImageOnLoad"
      @error="handleOnError"
      :class="imgClass"
      v-bind="otherAttrs"
    />
    <template v-if="$slots.fallbackIcon && failed">
      <slot name="fallbackIcon" />
    </template>
    <i v-else-if="failed && fallbackIconClass" :class="fallbackIconClass" />
    <figcaption class="text-center text-[8px]">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { ref, useAttrs, computed } from "vue";
import ProgressSpinner from "primevue/progressspinner";

const imgLoading = ref(true);
const failed = ref<boolean>(false);

const props = withDefaults(
  defineProps<{
    className?: string;
    width?: number;
    fallbackIconClass?: string;
    caption?: string;
  }>(),
  {
    fallbackIconClass: "pi pi-image",
  },
);

const imgClass = computed(() =>
  props.className
    ? { [props.className]: props.className, loading: imgLoading.value }
    : {
        loading: imgLoading.value,
      },
);

const otherAttrs = useAttrs();

const handleImageOnLoad = () => {
  failed.value = false;
  imgLoading.value = false;
};
const handleOnError = () => {
  failed.value = true;
  imgLoading.value = false;
};
</script>

<style scoped lang="scss">
.loading {
  opacity: 0;
  position: absolute;
  left: 100000px;
}
</style>
