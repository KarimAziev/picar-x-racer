<template>
  <div class="flex flex-wrap items-center">
    <div class="font-medium">Lines:</div>
    <Popover
      @show="handleSelectBeforeShow"
      @hide="handleSelectBeforeHide"
      :style="{ color: store.keypointsColor || 'var(--p-primary-500)' }"
      label="All"
    >
      <PoseSettings
        title="Edit all lines"
        :color-picker-id="`skeleton-global-line`"
        v-model:color="store.skeletonColor"
        v-model:size="store.skeletonSize"
        :initialSize="defaultState.skeletonSize"
        :initialColor="defaultState.skeletonColor"
        :isResetDisabled="isResetDisabled"
        @update:color="store.updateSkeletonColor"
        @update:size="store.updateSkeletonSize"
        @reset="
          () => {
            store.skeletonColor = defaultState.skeletonColor;
            store.skeletonSize = defaultState.skeletonSize;
            store.lines = cloneDeep(defaultState.lines);
          }
        "
      />
    </Popover>
    <Popover
      v-for="(obj, name) in store.lines"
      :style="{ color: obj.color || 'var(--p-primary-500)' }"
      :key="name"
      @show="handleSelectBeforeShow"
      @hide="handleSelectBeforeHide"
      :label="startCase(name)"
    >
      <PoseSettings
        showFiberSettings
        :title="`Edit ${startCase(name)}`"
        :color-picker-id="`skeleton-line-${name}`"
        v-model:color="store.lines[name].color"
        v-model:size="store.lines[name].size"
        v-model:render-fiber="store.lines[name].renderFiber"
        :initialSize="defaultState.lines[name].size"
        :initialColor="defaultState.lines[name].color"
        :initial-fiber="defaultState.lines[name].renderFiber"
      />
    </Popover>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useThemeStore, usePopupStore } from "@/features/settings/stores";
import { startCase } from "@/util/str";
import Popover from "@/ui/Popover.vue";
import { defaultState } from "@/features/settings/stores/theme";
import { isObjectShallowEquals, cloneDeep } from "@/util/obj";
import { OverlayLinesParams } from "@/features/detection/interface";
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
    (store.skeletonColor === defaultState.skeletonColor ||
      store.skeletonColor === store.primaryColor) &&
    Object.entries(defaultState.lines).every(([key, value]) =>
      isObjectShallowEquals(
        value,
        store.lines[key as keyof OverlayLinesParams],
      ),
    ),
);
</script>
