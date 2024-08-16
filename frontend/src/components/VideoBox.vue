<template>
  <div class="video-box">
    <img :src="imgPath" width="1280" height="720" alt="Video" />
  </div>
</template>
<script setup lang="ts">
const imgPath = "/mjpg";
</script>

<style scoped>
@import "/src/assets/scss/variables.scss";

.video-box {
  width: 100%;
  height: 100vh;
  text-align: center;
  justify-items: center;
  justify-content: center;
  display: flex;
  align-items: center;
  font-weight: bold;
  font-size: 20px;
  background: var(--video-bg-color);
}

.video-box > img {
  min-width: 1280px;
  min-height: 720px;
  max-height: 100vh;
}
</style>
