<template>
  <div class="scanlines" v-bind="attrs">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { useAttrs } from "vue";

const attrs = useAttrs();
</script>

<style scoped lang="scss">
.scanlines {
  box-shadow: 0px 0px 4px 2px var(--robo-color-primary);
  position: relative;
  background-color: transparent;
}

.scanlines:after {
  display: block;
  pointer-events: none;
  content: "";
  position: absolute;
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

@keyframes scanlines {
  0% {
    background-position: 0 50%;
  }
}
</style>
