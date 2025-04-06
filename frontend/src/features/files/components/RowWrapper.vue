<template>
  <div
    :tabindex="tabindex"
    :draggable="!isEditing && draggable && !disabled"
    @dragstart="handleDragStart"
    @dragend="handleDragEnd"
    @dragover="handleDragOver"
    @drop="handleDrop"
    v-if="Object.hasOwn(levelClasses, level)"
    :class="[levelClasses[level], 'focus:outline-none']"
  >
    <slot></slot>
  </div>
  <div
    v-else
    :tabindex="tabindex"
    :draggable="draggable && !disabled"
    @dragstart="handleDragStart"
    @dragend="handleDragEnd"
    @dragover="handleDragOver"
    @drop="handleDrop"
    :class="'focus:outline-none focus:ring-2 focus:ring-primary-500'"
    :style="{
      paddingLeft: level + 1 + 'rem',
    }"
  >
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { inject, Ref, computed } from "vue";
import { useActiveElement } from "@vueuse/core";

import { UploadingFileDetail } from "@/features/files/interface";
import { isInput } from "@/util/guards";

export interface Props extends Pick<UploadingFileDetail, "path" | "children"> {
  level?: number;
  disabled?: boolean;
  draggable?: boolean;
  tabindex?: number;
}
const emit = defineEmits(["move", "toggle:expand"]);

const activeEl = useActiveElement();

const levelClasses: Record<number, string> = {
  0: "ml-[1rem]",
  1: "ml-[2rem]",
  2: "ml-[3rem]",
  3: "ml-[4rem]",
  4: "ml-[5rem]",
  5: "ml-[6rem]",
  6: "ml-[7rem]",
  7: "ml-[8rem]",
  8: "ml-[9rem]",
  9: "ml-[10rem]",
};

const props = withDefaults(defineProps<Props>(), {
  level: 0,
  draggable: true,
});

const markedNodes = inject<Ref<Record<string, boolean>>>("markedNodes");
const isEditing = computed(() => isInput(activeEl.value));

const handleDragStart = (event: DragEvent) => {
  if (isInput(activeEl.value)) {
    return;
  }

  let dragPayload: string[] = [];
  if (markedNodes?.value && markedNodes?.value[props.path]) {
    dragPayload = Object.keys(markedNodes.value).filter(
      (key) => markedNodes.value[key],
    );
  } else {
    dragPayload = [props.path];
  }

  event.dataTransfer?.setData("application/json", JSON.stringify(dragPayload));
  event.dataTransfer!.effectAllowed = "move";
};

const handleDragEnd = () => {};

const handleDrop = (event: DragEvent) => {
  event.preventDefault();
  const data = event.dataTransfer?.getData("application/json");
  if (data) {
    const filePaths: string[] = JSON.parse(data);

    const filteredPaths = filePaths.filter((p) => p !== props.path);
    if (filteredPaths.length > 0) {
      emit("move", props.path, filePaths);
    }
  }
};

const handleDragOver = (event: DragEvent) => {
  event.preventDefault();
};
</script>
