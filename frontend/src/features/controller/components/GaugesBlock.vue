<template>
  <div class="gauges-block gap-5" :class="classObj">
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
    <Messages v-if="isMobile" class="messages" />
  </div>
</template>
<script setup lang="ts">
import { defineAsyncComponent, computed } from "vue";
import ToggleableView from "@/ui/ToggleableView.vue";
import { useDeviceWatcher } from "@/composables/useDeviceWatcher";
import Messages from "@/features/messager/components/MessageListContainer.vue";

const isMobile = useDeviceWatcher();

const classObj = computed(() => (isMobile.value ? "mobile" : ""));

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

<style scoped lang="scss">
.gauges-block {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: fit-content;

  right: 0;
  bottom: 0;
}
.gauges-block.mobile {
  top: 40px;
  left: 10px;
  width: 40%;

  @media screen and (min-width: 768px) {
    width: 150px;
  }
  @media (min-width: 992px) {
    width: 200px;
  }

  @media (min-width: 1200px) {
    width: 220px;
  }
}
.messages {
  max-height: 50px;
  overflow-y: scroll;
  font-size: 0.8rem;
  @media screen and (min-height: 390px) {
    max-height: 80px;
  }
}
</style>
