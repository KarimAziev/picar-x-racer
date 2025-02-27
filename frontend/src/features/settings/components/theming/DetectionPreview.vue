<template>
  <div ref="canvasWrapper" class="h-[480px] relative">
    <div class="absolute top-[10px] right-[5px] z-[10000] color-primary">
      <ButtonIcon
        v-tooltip="'Animate'"
        @click="toggleAnimation"
        :icon="`pi ${isAnimateEnabled ? 'pi-stop-circle' : 'pi-play-circle'}`"
      ></ButtonIcon>
      <ButtonIcon
        class="p-2"
        @click="handleZoomOut"
        v-tooltip="'Zoom out'"
        icon="pi pi-search-minus"
      ></ButtonIcon>
      <ButtonIcon
        class="p-2"
        v-tooltip="'Zoom in'"
        @click="handleZoomIn"
        icon="pi pi-search-plus"
      ></ButtonIcon>
      <div class="flex justify-end">
        <ButtonIcon
          v-tooltip="'Move left'"
          @click="handleMoveLeft"
          icon="pi pi-arrow-left"
        ></ButtonIcon>
        <div class="flex flex-col">
          <ButtonIcon
            v-tooltip="'Move up'"
            @click="handleMoveUp"
            icon="pi pi-arrow-up"
          ></ButtonIcon>
          <ButtonIcon
            v-tooltip="'Move down'"
            @click="handleMoveDown"
            icon="pi pi-arrow-down"
          ></ButtonIcon>
        </div>
        <ButtonIcon
          v-tooltip="'Move right'"
          @click="handleMoveRight"
          icon="pi pi-arrow-right"
        ></ButtonIcon>
      </div>
    </div>
    <div
      class="absolute top-[10px] left-[10px] z-[10000] text-[0.8rem] leading-[1.3] color-primary"
    >
      <div class="flex flex-col" v-if="isHelpOpen">
        <div>
          Click on a line or keypoint to edit.
          <ButtonIcon
            @click="isHelpOpen = false"
            icon="pi pi-times"
          ></ButtonIcon>
        </div>
        <div>Drag the mouse to move the object.</div>
        <div>Hold Ctrl while dragging to rotate the object.</div>
        <div>Use the mouse wheel to zoom in and out.</div>
      </div>
      <div v-else>
        <ButtonIcon
          v-tooltip="'Click to see the help'"
          @click="isHelpOpen = true"
          icon="pi pi-question-circle"
        ></ButtonIcon>
      </div>
    </div>
  </div>
  <Popover
    ref="popoverRef"
    @show="handleSelectBeforeShow"
    @hide="handleSelectBeforeHide"
  >
    <PoseSettings
      showFiberSettings
      v-if="popoverData?.type === 'skeleton'"
      :color-picker-id="`${popoverData?.type}-${popoverData?.group}`"
      :title="`Edit ${startCase(popoverData?.type)}'s ${startCase(popoverData?.group)}`"
      :group="popoverData.group"
      v-model:color="
        store.lines[popoverData.group as keyof OverlayLinesParams].color
      "
      v-model:size="
        store.lines[popoverData.group as keyof OverlayLinesParams].size
      "
      v-model:render-fiber="
        store.lines[popoverData.group as keyof OverlayLinesParams].renderFiber
      "
      :initialSize="
        defaultState.lines[popoverData.group as keyof OverlayLinesParams].size
      "
      :initialColor="
        defaultState.lines[popoverData.group as keyof OverlayLinesParams].color
      "
      :initial-fiber="
        defaultState.lines[popoverData.group as keyof OverlayLinesParams]
          .renderFiber
      "
    />
    <PoseSettings
      v-else-if="popoverData?.type === 'keypoint'"
      :color-picker-id="`${popoverData?.type}-${popoverData?.group}`"
      :title="`Edit ${startCase(popoverData?.type)}'s ${startCase(popoverData?.group)}`"
      :group="popoverData.group"
      v-model:color="
        store.keypoints[popoverData.group as KeypointGroupProp].color
      "
      v-model:size="
        store.keypoints[popoverData.group as KeypointGroupProp].size
      "
      :initialSize="
        defaultState.keypoints[popoverData.group as KeypointGroupProp].size
      "
      :initialColor="
        defaultState.keypoints[popoverData.group as KeypointGroupProp].color
      "
    />

    <DetectionBoxes
      v-else-if="popoverData?.type === 'bbox'"
      :color-picker-id="`${popoverData?.type}-${popoverData?.group}`"
      title="Bbox"
    />
  </Popover>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import {
  DetectionPoseRenderer,
  Metadata,
} from "@/features/detection/overlays/pose/DetectionPoseRenderer";
import {
  detectionSample,
  skeletonKeypointsPreviewSample,
  getBoundingBox,
} from "@/features/settings/components/theming/config";
import { useThemeStore, usePopupStore } from "@/features/settings/stores";
import { useElementSize } from "@/composables/useElementSize";
import Popover from "primevue/popover";
import ButtonIcon from "@/ui/ButtonIcon.vue";

import type { PopoverMethods } from "primevue/popover";
import { useLocalStorage } from "@vueuse/core";
import { OverlayLinesParams } from "@/features/detection/interface";
import type { KeypointGroupProp } from "@/features/detection/interface";
import { startCase } from "@/util/str";
import DetectionBoxes from "@/features/settings/components/theming/DetectionBoxes.vue";
import { BODY_PARTS } from "@/features/detection/enums";
import { defaultState } from "@/features/settings/stores/theme";
import PoseSettings from "@/features/settings/components/theming/PoseSettings.vue";

const isHelpOpen = useLocalStorage("is-help-open", true);
const isAnimateEnabled = ref(false);

const store = useThemeStore();

const popupStore = usePopupStore();

const handleSelectBeforeShow = () => {
  popupStore.isEscapable = false;
};

const handleSelectBeforeHide = () => {
  popupStore.isEscapable = true;
};

const baseKeypoints = skeletonKeypointsPreviewSample.map((pt) => ({ ...pt }));

const amplitudeAnimation = ref(20);

const kneePhaseOffset = Math.PI;

let tStart = performance.now();

function animateWalking(now: number) {
  const amplitude = amplitudeAnimation.value;
  const t = (now - tStart) / 500;

  const animatedKeypoints = baseKeypoints.map((pt) => ({ ...pt }));

  const leftDisplacement = Math.sin(t) * amplitude;
  const rightDisplacement = Math.sin(t + kneePhaseOffset) * amplitude;

  animatedKeypoints[BODY_PARTS.LEFT_KNEE].y =
    baseKeypoints[BODY_PARTS.LEFT_KNEE].y + leftDisplacement;
  animatedKeypoints[BODY_PARTS.LEFT_ANKLE].y =
    baseKeypoints[BODY_PARTS.LEFT_ANKLE].y + leftDisplacement;

  animatedKeypoints[BODY_PARTS.RIGHT_KNEE].y =
    baseKeypoints[BODY_PARTS.RIGHT_KNEE].y + rightDisplacement;
  animatedKeypoints[BODY_PARTS.RIGHT_ANKLE].y =
    baseKeypoints[BODY_PARTS.RIGHT_ANKLE].y + rightDisplacement;

  animatedKeypoints[BODY_PARTS.LEFT_HIP].y =
    baseKeypoints[BODY_PARTS.LEFT_HIP].y + leftDisplacement * 0.3;
  animatedKeypoints[BODY_PARTS.RIGHT_HIP].y =
    baseKeypoints[BODY_PARTS.RIGHT_HIP].y + rightDisplacement * 0.3;

  animatedKeypoints[BODY_PARTS.LEFT_HIP].y =
    baseKeypoints[BODY_PARTS.LEFT_HIP].y + leftDisplacement * 0.3;
  animatedKeypoints[BODY_PARTS.RIGHT_HIP].y =
    baseKeypoints[BODY_PARTS.RIGHT_HIP].y + rightDisplacement * 0.3;

  animatedKeypoints[BODY_PARTS.LEFT_WRIST].y =
    baseKeypoints[BODY_PARTS.LEFT_WRIST].y + leftDisplacement * 0.3;
  animatedKeypoints[BODY_PARTS.RIGHT_WRIST].y =
    baseKeypoints[BODY_PARTS.RIGHT_WRIST].y + rightDisplacement * 0.3;

  const newBbox = getBoundingBox(animatedKeypoints);

  const animatedDetection = {
    bbox: newBbox,
    label: detectionSample.label,
    confidence: detectionSample.confidence,
    keypoints: animatedKeypoints,
  };

  if (rendererInstance.value) {
    rendererInstance.value.renderDetections(
      [animatedDetection],
      store.lines,
      store.keypoints,
      store.bboxesColor,
    );
  }

  if (isAnimateEnabled.value) {
    requestAnimationFrame(animateWalking);
  }
}

const toggleAnimation = () => {
  isAnimateEnabled.value = !isAnimateEnabled.value;
  if (isAnimateEnabled.value) {
    requestAnimationFrame(animateWalking);
  }
};

const canvasWrapper = ref<HTMLElement | null>(null);
const rendererInstance = ref<DetectionPoseRenderer | null>(null);
const popoverRef = ref<PopoverMethods>();
const wrapperSize = useElementSize(canvasWrapper);
const popoverData = ref<Metadata | null>(null);

const handleTogglePopover = (event: MouseEvent, data?: Metadata) => {
  if (!canvasWrapper.value) {
    return;
  }

  if (!data) {
    popoverData.value = null;
    popoverRef.value?.hide();
    return;
  }

  if (popoverRef.value && popoverData.value) {
    popoverData.value = null;
    popoverRef.value.hide();
    return setTimeout(() => handleTogglePopover(event, data), 150);
  }

  popoverData.value = data;

  const rect = canvasWrapper.value.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  const dummyAnchor = document.createElement("div");
  dummyAnchor.style.position = "absolute";
  dummyAnchor.style.left = `${x}px`;
  dummyAnchor.style.top = `${y}px`;
  dummyAnchor.style.width = "1px";
  dummyAnchor.style.height = "1px";
  dummyAnchor.style.pointerEvents = "none";
  canvasWrapper.value.appendChild(dummyAnchor);

  popoverRef.value?.show(event, dummyAnchor);
  setTimeout(() => dummyAnchor.remove(), 100);
};

const handleZoomIn = () => {
  if (rendererInstance.value) {
    rendererInstance.value.zoomIn();
  }
};

const handleZoomOut = () => {
  if (rendererInstance.value) {
    rendererInstance.value.zoomOut();
  }
};

const handleMoveUp = () => {
  rendererInstance.value?.moveUp();
};

const handleMoveDown = () => {
  rendererInstance.value?.moveDown();
};

const handleMoveLeft = () => {
  rendererInstance.value?.moveLeft();
};

const handleMoveRight = () => {
  rendererInstance.value?.moveRight();
};

onMounted(() => {
  if (canvasWrapper.value) {
    rendererInstance.value = new DetectionPoseRenderer(
      canvasWrapper.value,
      14,
      wrapperSize.width,
      wrapperSize.height,
      handleTogglePopover,
    );

    rendererInstance.value.renderDetections(
      [detectionSample],
      store.lines,
      store.keypoints,
      store.bboxesColor,
    );
    rendererInstance.value.alignToCenter();
    rendererInstance.value.zoomIn(0.5);
    requestAnimationFrame(animateWalking);
  }
});

watch(
  () => [
    wrapperSize.width,
    wrapperSize.height,
    store.primaryColor,
    store.bboxesColor,
    store.dark,
    store.lines,
    store.keypoints,
  ],
  () => {
    if (rendererInstance.value) {
      rendererInstance.value.setSize(wrapperSize.width, wrapperSize.height);
      rendererInstance.value.renderDetections(
        [detectionSample],
        store.lines,
        store.keypoints,
        store.bboxesColor,
      );
    }
  },
  { deep: true },
);

onBeforeUnmount(() => {
  rendererInstance.value?.dispose();
});
</script>
