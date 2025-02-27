<template>
  <div class="flex flex-wrap items-center">
    <div class="font-medium">Keypoints:</div>
    <Popover
      :style="{ color: store.keypointsColor || 'var(--p-primary-500)' }"
      label="All"
      @show="handleSelectBeforeShow"
      @hide="handleSelectBeforeHide"
    >
      <PoseSettings
        color-picker-id="keypoints-global-color"
        title="Edit all keypoints"
        v-model:color="store.keypointsColor"
        v-model:size="store.keypointsSize"
        :initialColor="defaultState.keypointsColor"
        :initialSize="defaultState.keypointsSize"
        @update:color="store.updateKeypointsColor"
        @update:size="store.updateKeypointsSize"
        :isResetDisabled="isResetDisabled"
        @reset="
          () => {
            store.keypointsColor = defaultState.keypointsColor;
            store.keypointsSize = defaultState.keypointsSize;
            store.keypoints = cloneDeep(defaultState.keypoints);
          }
        "
      />
    </Popover>
    <Popover
      :style="{ color: obj.color || 'var(--p-primary-500)' }"
      @show="handleSelectBeforeShow"
      @hide="handleSelectBeforeHide"
      v-for="(obj, name) in store.keypoints"
      :key="name"
      :label="startCase(name)"
    >
      <PoseSettings
        :color-picker-id="`pose-${name}`"
        :title="`Edit ${startCase(name)}`"
        v-model:color="store.keypoints[name].color"
        v-model:size="store.keypoints[name].size"
        :initialSize="defaultState.keypoints[name].size"
        :initialColor="defaultState.keypoints[name].color"
      />
    </Popover>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useThemeStore, usePopupStore } from "@/features/settings/stores";
import { startCase } from "@/util/str";
import Popover from "@/ui/Popover.vue";
import { isObjectShallowEquals, cloneDeep } from "@/util/obj";
import { defaultState } from "@/features/settings/stores/theme";
import { KeypointsParams } from "@/features/detection/interface";
import PoseSettings from "@/features/settings/components/theming/PoseSettings.vue";

const popupStore = usePopupStore();

const handleSelectBeforeShow = () => {
  popupStore.isEscapable = false;
};

const handleSelectBeforeHide = () => {
  popupStore.isEscapable = true;
};

const store = useThemeStore();
const isResetDisabled = computed(
  () =>
    defaultState.keypointsColor === store.keypointsColor &&
    Object.entries(defaultState.keypoints).every(([key, value]) =>
      isObjectShallowEquals(
        value,
        store.keypoints[key as keyof KeypointsParams],
      ),
    ),
);
</script>
