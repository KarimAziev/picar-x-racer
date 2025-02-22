<template>
  <Popover
    class="!py-0"
    label="All"
    text
    @show="handleSelectBeforeShow"
    @hide="handleSelectBeforeHide"
  >
    <ColorOptions
      color-picker-id="keypoints-color"
      v-model:color="store.keypointsColor"
      :options="colorOptions"
      @update:color="store.updateKeypointsColor"
    >
      <template #extra>
        <div>
          <span class="text-sm font-medium">Width: </span>
          <Slider
            class="w-32"
            :min="1"
            @update:model-value="(v) => store.updateKeypointsSize(v as number)"
            :max="100"
            v-model="store.keypointsSize"
          />
        </div>
      </template>
      <Button
        size="small"
        label="Reset"
        :disabled="isResetDisabled"
        @click="
          () => {
            store.keypointsColor = defaultState.keypointsColor;
            store.keypoints = cloneDeep(defaultState.keypoints);
          }
        "
      />
    </ColorOptions>
  </Popover>
  <Popover
    @show="handleSelectBeforeShow"
    @hide="handleSelectBeforeHide"
    v-for="(obj, name) in store.keypoints"
    :key="name"
    :label="startCase(name)"
    text
    class="!py-0"
  >
    <ColorOptions
      :color-picker-id="`skeleton-keypoint-${name}`"
      v-model:color="obj.color"
      @update:color="
        (v: string) => {
          store.keypoints[name].color = v;
        }
      "
      :options="colorOptions"
    >
      <template #extra>
        <div>
          <span class="text-sm font-medium">Width: </span>
          <Slider class="w-32" :min="1" :max="100" v-model="obj.size" />
        </div>
      </template>
      <Button
        label="Reset"
        size="small"
        :disabled="
          isObjectShallowEquals(
            store.keypoints[name],
            cloneDeep(defaultState.keypoints[name]),
          )
        "
        @click="
          () => {
            store.keypoints[name] = { ...defaultState.keypoints[name] };
          }
        "
      />
    </ColorOptions>
  </Popover>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { colorOptions } from "@/features/settings/components/theming/colors";
import { useThemeStore, usePopupStore } from "@/features/settings/stores";
import ColorOptions from "@/features/settings/components/theming/ColorOptions.vue";
import { startCase } from "@/util/str";
import Popover from "@/ui/Popover.vue";
import { isObjectShallowEquals, cloneDeep } from "@/util/obj";
import { defaultState } from "@/features/settings/stores/theme";
import { KeypointsParams } from "@/types/overlay";

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
