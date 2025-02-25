<template>
  <div class="flex flex-wrap items-center">
    <div class="font-medium">Lines:&nbsp;</div>
    <Popover @show="handleSelectBeforeShow" @hide="handleSelectBeforeHide">
      <template #button="{ toggle }">
        <Button
          class="!py-0"
          text
          @click="toggle"
          v-tooltip="'Click to customize all pose lines'"
          :style="{ color: store.skeletonColor || 'var(--p-primary-500)' }"
        >
          All
          <SkeletonIcon width="20px" height="20px" />
        </Button>
      </template>
      <ColorOptions
        color-picker-id="skeleton-color"
        v-model:color="store.skeletonColor"
        :options="colorOptions"
        @update:color="store.updateSkeletonColor"
      >
        <template #extra>
          <div>
            <span class="text-sm font-medium">Width: </span>
            <Slider
              class="w-32"
              :min="1"
              @update:model-value="
                (v: number | number[]) => store.updateSkeletonSize(v as number)
              "
              :max="100"
              v-model="store.lines.torso.size"
            />
          </div>
        </template>
        <Button
          size="small"
          label="Reset"
          :disabled="isResetDisabled"
          @click="
            () => {
              store.skeletonColor = defaultState.skeletonColor;
              store.lines = cloneDeep(defaultState.lines);
            }
          "
        />
      </ColorOptions>
    </Popover>
    <Popover
      v-for="(obj, name) in store.lines"
      :key="name"
      @show="handleSelectBeforeShow"
      @hide="handleSelectBeforeHide"
    >
      <template #button="{ toggle }">
        <Button
          text
          class="!py-0"
          :label="startCase(name)"
          @click="toggle"
          v-tooltip="`Customize ${startCase(name)}`"
          :style="{ color: obj.color || 'var(--p-primary-500)' }"
        >
          {{ startCase(name) }}
          <component
            v-if="linesIcons[name]"
            :is="linesIcons[name]"
            width="20px"
            height="20px"
          />
        </Button>
      </template>
      <ColorOptions
        :color-picker-id="`skeleton-line-${name}`"
        v-model:color="store.lines[name].color"
        :options="colorOptions"
        @update:color="
          (v: string) => {
            store.lines[name].color = v;
          }
        "
      >
        <template #extra>
          <div class="flex items-center gap-4">
            <div class="font-medium">
              Render Skeleton Fibers
              <span
                class="relative hover:opacity-80 transition-opacity duration-200 ease-in-out after:content-['?'] after:text-[0.8rem] after:text-blue-500 after:relative after:-top-[5px] after:pointer-events-none"
                v-tooltip="
                  'When enabled, the setting overlays additional curved lines along the primary skeleton connections. These extra fibers simulate muscle, adding depth and a more three-dimensional feel to the detected pose.'
                "
              ></span>
            </div>
            <Checkbox v-model="store.lines[name].renderFiber" binary />
          </div>

          <div>
            <span class="text-sm font-medium">Width: </span>
            <Slider class="w-32" :min="0" :max="100" v-model="obj.size" />
          </div>
        </template>
        <Button
          label="Reset"
          size="small"
          :disabled="
            isObjectShallowEquals(
              cloneDeep(defaultState.lines[name]),
              store.lines[name],
            )
          "
          @click="
            () => {
              store.lines[name] = { ...defaultState.lines[name] };
            }
          "
        />
      </ColorOptions>
    </Popover>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { colorOptions } from "@/features/settings/components/theming/colors";
import { useThemeStore, usePopupStore } from "@/features/settings/stores";
import ColorOptions from "@/features/settings/components/theming/ColorOptions.vue";
import { startCase } from "@/util/str";
import Popover from "@/ui/Popover.vue";
import ArmIcon from "@/ui/icons/ArmIcon.vue";
import TorsoIcon from "@/ui/icons/TorsoIcon.vue";
import LegsIcon from "@/ui/icons/LegsIcon.vue";
import SkullIcon from "@/ui/icons/SkullIcon.vue";
import SkeletonIcon from "@/ui/icons/SkeletonIcon.vue";
import { defaultState } from "@/features/settings/stores/theme";
import { isObjectShallowEquals, cloneDeep } from "@/util/obj";
import { OverlayLinesParams } from "@/features/detection/interface";

const popupStore = usePopupStore();

const handleSelectBeforeShow = () => {
  popupStore.isEscapable = false;
};

const handleSelectBeforeHide = () => {
  popupStore.isEscapable = true;
};

const linesIcons = {
  head: SkullIcon,
  torso: TorsoIcon,
  arms: ArmIcon,
  legs: LegsIcon,
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
