<template>
  <div class="relative w-full h-full flex flex-col justify-center items-center">
    <ProgressSpinner
      :style="`width: ${width}px;`"
      class="auto my-auto text-center"
      v-if="imgLoading"
    />
    <img
      class="auto transition-opacity cursor-pointer"
      @load="handleImageOnLoad"
      :class="imgClass"
      :style="`width: ${width}px;`"
      v-bind="otherAttrs"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, useAttrs, computed } from "vue";
import ProgressSpinner from "primevue/progressspinner";
const imgLoading = ref(true);

const props = defineProps<{ className?: string; width?: number }>();

const imgClass = computed(() =>
  props.className
    ? { [props.className]: props.className, loading: imgLoading.value }
    : {
        loading: imgLoading.value,
      },
);

const otherAttrs = useAttrs();

const handleImageOnLoad = () => {
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
