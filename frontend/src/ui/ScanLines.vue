<template>
  <div class="scanlines" :class>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
defineProps<{ class?: string }>();
</script>

<style scoped lang="scss">
.scanlines {
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);

  position: relative;
  background-color: transparent;
}
.scanlines:before,
.scanlines:after {
  display: block;
  pointer-events: none;
  content: "";
  position: absolute;
}
.scanlines:before {
  width: 100%;
  height: 2px;
  background: transparent;
  opacity: 0.55;
  animation: scanline 6s linear infinite;
}
.scanlines:after {
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;

  background: linear-gradient(
    to bottom,
    transparent 50%,
    var(--robo-color-primary) 51%
  );
  background-size: 100% 4px;
  animation: scanlines 2s steps(60) infinite;
}

@keyframes scanline {
  0% {
    transform: translate3d(0, 200000%, 0);
  }
}
@keyframes scanlines {
  0% {
    background-position: 0 50%;
  }
}
</style>
