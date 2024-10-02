<template>
  <div class="box">
    <ProgressSpinner
      :style="`width: ${width}px;`"
      class="preloader"
      v-if="imgLoading"
    />
    <img
      class="image-preview"
      @load="handleImageOnLoad"
      :style="`width: ${width}px;`"
      :class="imgClass"
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
.box {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
}
.preloader {
  height: auto;
  text-align: center;
  margin: auto;
  flex: auto;
}
.image-preview {
  height: auto;
}
.loading {
  opacity: 0;
  position: absolute;
  left: 100000px;
}
</style>
