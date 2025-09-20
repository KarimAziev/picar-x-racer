<template>
  <div
    ref="textEl"
    class="whitespace-pre-wrap break-words transition-all duration-300"
    :class="{
      [lineClampClass]: !expanded,
      'cursor-pointer': isEnabled,
    }"
    @click="toggle"
  >
    <ButtonIcon
      v-if="isEnabled"
      icon="pi pi-sort-down-fill"
      :class="{ '-rotate-90': !expanded }"
    />
    {{ text }}
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from "vue";
import ButtonIcon from "@/ui/ButtonIcon.vue";

const props = defineProps<{ text: string; lineClampClass: string }>();
const expanded = ref(false);
const textEl = ref<HTMLElement | null>(null);
const needsToggle = ref(false);

const isEnabled = computed(() => needsToggle.value || expanded.value);

const checkOverflow = () => {
  if (!textEl.value) return;
  needsToggle.value = textEl.value.scrollHeight > textEl.value.clientHeight;
};

const toggle = () => {
  if (isEnabled.value) {
    expanded.value = !expanded.value;
    nextTick(checkOverflow);
  }
};

let ro: ResizeObserver | null = null;
let mo: MutationObserver | null = null;
const onResizeObserved = () => {
  nextTick(checkOverflow);
};

onMounted(() => {
  nextTick(checkOverflow);

  if (typeof ResizeObserver !== "undefined") {
    ro = new ResizeObserver(onResizeObserved);
    if (textEl.value) ro.observe(textEl.value);
  } else {
    window.addEventListener("resize", onResizeObserved);
  }

  if (typeof MutationObserver !== "undefined" && textEl.value) {
    mo = new MutationObserver(onResizeObserved);
    mo.observe(textEl.value, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  if (textEl.value) {
    textEl.value.addEventListener("transitionend", onResizeObserved);
  }

  if ((document as any).fonts && (document as any).fonts.ready) {
    (document as any).fonts.ready.then(() => nextTick(checkOverflow));
  }
});

onUnmounted(() => {
  if (ro) {
    ro.disconnect();
    ro = null;
  }
  if (mo) {
    mo.disconnect();
    mo = null;
  }
  window.removeEventListener("resize", onResizeObserved);
  if (textEl.value) {
    textEl.value.removeEventListener("transitionend", onResizeObserved);
  }
});

watch(
  () => props.text,
  () => {
    expanded.value = false;
    nextTick(checkOverflow);
  },
);
</script>
