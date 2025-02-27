<template>
  <SelectField
    :class="class"
    optionLabel="label"
    optionValue="value"
    label="Video Effect"
    field="video_feed_enhance_mode"
    tooltipHelp="Video effect to apply"
    tooltip="%s"
    placeholder="Effect"
    v-model="streamStore.data.enhance_mode"
    :loading="streamStore.loading"
    :options="enhancers"
    @update:model-value="updateStreamParams"
  />
</template>

<script setup lang="ts">
import { onMounted, computed } from "vue";
import SelectField from "@/ui/SelectField.vue";
import { useStreamStore } from "@/features/settings/stores";
import { objectKeysToOptions } from "@/features/settings/util";
import { useAsyncDebounce } from "@/composables/useDebounce";

const streamStore = useStreamStore();

defineProps<{ class?: string }>();

const enhancers = computed(() => [
  ...objectKeysToOptions(streamStore.enhancers),
  { label: "None", value: null },
]);

const updateStreamParams = useAsyncDebounce(async () => {
  await streamStore.updateData(streamStore.data);
}, 500);

onMounted(async () => {
  if (!streamStore.enhancers.length) {
    await streamStore.fetchEnhancers();
  }
});
</script>
