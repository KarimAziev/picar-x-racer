<template>
  <div class="gauges-block gap-5" :class="class">
    <ToggleableView setting="text_to_speech_input">
      <TextToSpeechInput class="tts" v-if="isMobile" />
    </ToggleableView>
    <ToggleableView setting="text_info_view">
      <TextInfo />
    </ToggleableView>
    <slot></slot>
    <ToggleableView setting="speedometer_view" v-if="!isMobile">
      <Speedometer />
    </ToggleableView>
    <Messages v-if="isMobile" class="messages" />
  </div>
</template>
<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import ToggleableView from "@/ui/ToggleableView.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import TextToSpeechInput from "@/ui/tts/TextToSpeechInput.vue";
import Messages from "@/features/messager/components/MessageListContainer.vue";

const isMobile = useDeviceWatcher();

defineProps<{ class?: string }>();

const TextInfo = defineAsyncComponent({
  loader: () => import("@/features/controller/components/TextInfo.vue"),
});

const Speedometer = defineAsyncComponent({
  loader: () => import("@/features/controller/components/Speedometer.vue"),
});
</script>

<style scoped lang="scss">
.gauges-block {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: fit-content;

  @media (min-width: 992px) {
    right: 0;
    bottom: 0;
  }

  @media screen and (max-width: 992px) and (orientation: portrait) {
    left: 10px;
    top: 20px;
  }

  @media screen and (max-width: 992px) and (orientation: landscape) {
    left: 10px;
    top: 50px;
  }
}
.messages {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  margin-block-start: 0em;
  margin-block-end: 0em;
  margin-inline-start: 0px;
  margin-inline-end: 0px;
  padding-inline-start: 0px;
  max-height: 50px;
  overflow-y: scroll;
  font-size: 0.8rem;
}
</style>
