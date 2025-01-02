<template>
  <div
    :class="[
      'absolute flex flex-col items-start right-0 bottom-0 gap-x-1.5',
      isMobile
        ? 'top-10 left-2 w-[40%] sm:w-[150px] md:w-[200px] lg:w-[220px]'
        : '',
    ]"
  >
    <slot></slot>
    <ToggleableView v-if="isMobile" setting="general.text_to_speech_input">
      <TextToSpeechInput />
    </ToggleableView>
    <ToggleableView setting="general.text_info_view">
      <TextInfo />
    </ToggleableView>
    <ToggleableView setting="general.speedometer_view" v-if="!isMobile">
      <Speedometer />
    </ToggleableView>
    <Messages
      v-if="isMobile"
      class="max-h-[50px] overflow-y-scroll text-xs sm:max-h-[80px]"
    />
  </div>
</template>
<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import ToggleableView from "@/ui/ToggleableView.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import Messages from "@/features/messager/components/MessageListContainer.vue";

const isMobile = useDeviceWatcher();

const TextToSpeechInput = defineAsyncComponent({
  loader: () => import("@/ui/tts/TextToSpeechInput.vue"),
});
const TextInfo = defineAsyncComponent({
  loader: () => import("@/features/controller/components/TextInfo.vue"),
});

const Speedometer = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Speedometer.vue"),
});
</script>
