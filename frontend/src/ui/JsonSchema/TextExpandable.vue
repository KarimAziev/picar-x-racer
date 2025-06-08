<template>
  <ExpandableText
    v-if="text"
    :class="{
      'truncated-label': level >= 2,
      'max-w-[280px] min-[400px]:max-w-[380px] md:max-w-[420px] lg:max-w-[440px] xl:max-w-[540px] 2xl:max-w-[490px]':
        level < 2,
    }"
    :text="text"
    lineClampClass="line-clamp-1"
  ></ExpandableText>
  <Divider v-if="text && level < 2" />
</template>

<script setup lang="ts">
import ExpandableText from "@/ui/ExpandableText.vue";

defineProps<{ text?: string; level: number }>();
</script>
