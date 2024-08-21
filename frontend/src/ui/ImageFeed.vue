<template>
  <img :src="imgPath" class="image-feed" alt="Video" />
</template>

<script setup lang="ts">
const imgPath = "/mjpg";
</script>

<style scoped lang="scss">
.image-feed {
  width: 100%;
  display: block;
  height: 100%;
  object-fit: contain;
  user-select: none;
}
</style>
