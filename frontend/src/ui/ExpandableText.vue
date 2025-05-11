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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from "vue";
import ButtonIcon from "@/ui/ButtonIcon.vue";

interface Props {
  text: string;
  lineClampClass: string;
}

const props = defineProps<Props>();

const expanded = ref(false);

const textEl = ref<HTMLElement | null>(null);

const needsToggle = ref(false);

const isEnabled = computed(() => needsToggle.value || expanded.value);

const checkOverflow = () => {
  if (textEl.value) {
    needsToggle.value = textEl.value.scrollHeight > textEl.value.clientHeight;
  }
};

const toggle = () => {
  if (isEnabled.value) {
    expanded.value = !expanded.value;
    nextTick(checkOverflow);
  }
};

onMounted(() => {
  nextTick(checkOverflow);
});

watch(
  () => props.text,
  () => {
    expanded.value = false;
    nextTick(checkOverflow);
  },
);
</script>
