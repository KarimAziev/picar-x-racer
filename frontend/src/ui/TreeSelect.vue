<template>
  <button
    :disabled="disabled || loading"
    ref="btnRef"
    class="tree-btn w-full flex justify-between pl-3 border transition-colors border-form-field-border rounded-form-field text-form-field-color bg-form-field-background disabled:text-form-field-disabled-color focus:not-disabled:border-form-field-focus-border-color hover:not-disabled:not-focus:border-form-field-hover-border-color"
    type="button"
    @click="toggle"
  >
    <span
      class="truncate"
      :class="{ 'text-form-field-placeholder': !modelValue }"
    >
      {{ (modelValue && modelValue[labelProp]) || placeholder }}
    </span>

    <i
      class="pi pi-angle-down pt-1 md:pt-1.5 pr-2 text-form-field-icon-color"
      :class="{ 'text-form-field-disabled-color': disabled || loading }"
    />
  </button>

  <Popover
    ref="op"
    closeOnEscape
    @show="handleSelectBeforeShow"
    @hide="handleSelectBeforeHide"
  >
    <div class="relative min-w-72 flex flex-col" :class="popoverContentClass">
      <template v-if="$slots.header">
        <slot name="header"></slot>
      </template>
      <template v-if="$slots.footer">
        <slot name="footer"></slot>
      </template>
      <div
        :class="listClass"
        ref="listContainer"
        class="relative min-h-[300px]"
      >
        <VirtualTree
          :itemSize="itemSize"
          :label-prop="labelProp"
          :keyProp="keyProp"
          :nodes="nodes"
          ref="virtualTree"
        >
          <template #row="{ node, options }">
            <RowWrapper
              v-tooltip="{
                value: node.tooltip || node[labelProp],
                pt: {
                  root: {
                    style: 'width: max-content; display: flex;',
                  },
                  text: {
                    style: 'white-space: pre;',
                  },
                },
              }"
              @click="handleSelectOrExpand(node)"
              class="grid grid-cols-[10%_90%] gap-y-2 items-center h-[40px] focus:border focus:border-form-field-focus-border-color relative px-2 transition"
              :draggable="false"
              :data-virtual-index="options.index"
              :path="node[keyProp]"
              :tabindex="options.index + 1"
              @keydown="handleListKeydown"
              v-bind="omit(['path'], node)"
              :class="{
                [rowClass as string]: !!rowClass,
                'cursor-pointer': selectable(node) || node.children,
                'hover:bg-mask': !isNodeSelected(node),
                'bg-highlight': isNodeSelected(node) || hasSelectedChild(node),
              }"
            >
              <template v-if="$slots.nodeExpand">
                <slot
                  name="nodeExpand"
                  :path="node[keyProp]"
                  :children="node.children"
                  v-bind="node"
                ></slot>
              </template>
              <NodeExpand
                v-else
                :path="node[keyProp]"
                :children="node.children"
              />

              <template v-if="$slots.nodeLabel">
                <slot
                  name="nodeLabel"
                  class="block truncate"
                  :label="node.label"
                  v-bind="node"
                ></slot>
              </template>
              <div class="block truncate" v-else>
                {{ node && node[labelProp] }}
              </div>
            </RowWrapper>
          </template>
        </VirtualTree>
      </div>
    </div>
  </Popover>
</template>

<script setup lang="ts">
import { ref, provide, useTemplateRef, nextTick } from "vue";
import Popover from "primevue/popover";

import type { TreeNode } from "@/types/tree";
import type { Props as TreeProps } from "@/features/files/components/VirtualTree.vue";
import VirtualTree from "@/features/files/components/VirtualTree.vue";
import RowWrapper from "@/features/files/components/RowWrapper.vue";
import NodeExpand from "@/features/files/components/Cells/NodeExpand.vue";
import { useSettingsStore, usePopupStore } from "@/features/settings/stores";
import { getExpandableIds } from "@/features/files/components/util";
import { inRange } from "@/util/number";

import { formatKeyEventItem } from "@/util/keyboard-util";
import { isNumber } from "@/util/guards";
import { omit } from "@/util/obj";

const emit = defineEmits(["update:modelValue", "hide", "show"]);

const listContainer = ref<HTMLElement | null>(null);

export interface Props extends TreeProps {
  loading?: boolean;
  disabled?: boolean;
  modelValue: TreeNode | null;
  selectable?: (node: TreeNode) => boolean;
  listClass?: string;
  placeholder?: string | null;
  popoverContentClass?: string;
}

const virtualTree = useTemplateRef("virtualTree");
const op = ref<InstanceType<typeof Popover>>();
const btnRef = ref<HTMLButtonElement>();
const settingsStore = useSettingsStore();
const popupStore = usePopupStore();
const expandedNodes = ref<Set<string>>(new Set());
const markedNodes = ref<Record<string, boolean>>({});

const handleSelectBeforeShow = () => {
  settingsStore.inhibitKeyHandling = true;
  popupStore.isEscapable = false;
  moveFocus(0);
  addKeyEventListeners();
  emit("show");
};

const handleSelectBeforeHide = () => {
  settingsStore.inhibitKeyHandling = false;
  popupStore.isEscapable = true;
};

const expandAll = () => {
  expandedNodes.value = getExpandableIds(props.keyProp, props.nodes);
};

const props = withDefaults(defineProps<Props>(), {
  labelProp: "label",
  keyProp: "key",
  selectable: (node: TreeNode) => node.selectable,
});

const toggleExpand = (path: string) => {
  if (expandedNodes.value.has(path)) {
    expandedNodes.value.delete(path);
  } else {
    expandedNodes.value.add(path);
  }
};

const toggle = (event: MouseEvent) => {
  op.value?.toggle(event);
};

const handleClose = () => {
  removeKeyEventListeners();
  op.value?.hide();
  emit("hide");
};

const handleToggleExpandNode = (node: TreeNode) => {
  if (node.children) {
    toggleExpand(node[props.keyProp]);
  }
};

const isNodeSelected = (node: TreeNode) => {
  return !!(
    props.modelValue && props.modelValue[props.keyProp] === node[props.keyProp]
  );
};

const hasSelectedChild = (node: TreeNode) => {
  if (!props.modelValue || !node.children || node.children.length === 0) {
    return false;
  }

  const targetKey = props.modelValue[props.keyProp];

  // iterative DFS to avoid recursion depth issues
  const stack: TreeNode[] = [...node.children];
  while (stack.length) {
    const n = stack.pop()!;
    if (n[props.keyProp] === targetKey) {
      return true;
    }
    if (n.children && n.children.length) {
      stack.push(...n.children);
    }
  }

  return false;
};

const handleSelectOrExpand = (node: TreeNode, close: boolean = true) => {
  if (props.selectable(node)) {
    emit("update:modelValue", node);
    if (close) {
      handleClose();
    }
  } else {
    handleToggleExpandNode(node);
  }
};
const getCurrentNodeIndex = () => {
  const attrValue = document.activeElement?.getAttribute("data-virtual-index");
  if (attrValue) {
    return +attrValue;
  }
};

const moveToNextNode = () => {
  const currIdx = getCurrentNodeIndex();
  const range = virtualTree.value?.virtualScoller?.getRenderedRange();

  if (!range) {
    return;
  }

  const totalLen = virtualTree.value?.flatNodes.length;
  if (isNumber(totalLen) && totalLen - 1 === currIdx) {
    return;
  }

  const nextIndex = isNumber(currIdx) ? currIdx + 1 : null;
  if (nextIndex === null) {
    moveFocus(range.viewport.first);
    return;
  }

  const valid = inRange(nextIndex, range.viewport.first, range.viewport.last);

  if (valid) {
    moveFocus(nextIndex);
  } else {
    moveFocus(range.viewport.last);
  }
};
const moveToPrevNode = () => {
  const currIdx = getCurrentNodeIndex();
  const range = virtualTree.value?.virtualScoller?.getRenderedRange();

  if (!range) {
    return;
  }

  const nextIndex = isNumber(currIdx) ? currIdx - 1 : null;
  if (nextIndex === null) {
    moveFocus(range.viewport.first);
    return;
  }

  const valid = inRange(nextIndex, range.viewport.first, range.viewport.last);

  if (valid) {
    moveFocus(nextIndex);
  } else {
    virtualTree.value?.virtualScoller?.scrollToIndex(range.viewport.first - 1);
    nextTick(() => {
      moveFocus(range.viewport.first);
    });
  }
};

const handleMoveAndSelectNode = () => {
  const currIdx = getCurrentNodeIndex();
  if (!isNumber(currIdx)) {
    return;
  }
  const node = virtualTree.value?.flatNodes[currIdx];

  if (node) {
    handleSelectOrExpand(node, false);
  }
};

const handleExpandFocusedNode = () => {
  const currIdx = getCurrentNodeIndex();
  if (!isNumber(currIdx)) {
    return;
  }
  const node = virtualTree.value?.flatNodes[currIdx];

  if (node) {
    handleToggleExpandNode(node);
  }
};

const scrollRangeUp = () => {
  const range = virtualTree.value?.virtualScoller?.getRenderedRange();

  if (!range) {
    return;
  }
  virtualTree.value?.virtualScoller?.scrollTo({ top: 100 });
  moveFocus(range.viewport.first);
};

const scrollRangeDown = () => {
  const range = virtualTree.value?.virtualScoller?.getRenderedRange();

  if (!range) {
    return;
  }
  moveFocus(range.viewport.last);
};

const keymap: Record<string, () => void> = {
  "Ctrl-n": moveToNextNode,
  ArrowDown: moveToNextNode,
  "Ctrl-p": moveToPrevNode,
  ArrowUp: moveToPrevNode,
  Enter: handleMoveAndSelectNode,
  "Ctrl-v": scrollRangeDown,
  "Alt-v": scrollRangeUp,
  Space: handleExpandFocusedNode,
  Escape: handleClose,
  "Ctrl-g": handleClose,
};

const handleListKeydown = (event: KeyboardEvent) => {
  const key = formatKeyEventItem(event);

  const handler = keymap[key];

  if (!handler) {
    return;
  }

  event.stopPropagation();
  event.preventDefault();

  handler();
};

const addKeyEventListeners = () => {
  window.addEventListener("keydown", handleListKeydown);
};

const removeKeyEventListeners = () => {
  window.removeEventListener("keydown", handleListKeydown);
};

function moveFocus(newIndex: number) {
  if (!listContainer.value || !virtualTree.value?.virtualScoller) {
    return;
  }

  nextTick(() => {
    const range = virtualTree.value?.virtualScoller?.getRenderedRange();

    if (!range) {
      return;
    }

    const renderedElements = listContainer.value?.querySelectorAll<HTMLElement>(
      "[data-virtual-index]",
    );

    const nodeToFocus =
      listContainer.value?.querySelector<HTMLElement>(
        `[data-virtual-index="${newIndex}"]`,
      ) ||
      (renderedElements && renderedElements[0]);
    if (nodeToFocus) {
      nodeToFocus.focus();
    }
  });
}

provide("expandedNodes", expandedNodes);
provide("markedNodes", markedNodes);
defineExpose({
  expandAll,
  moveFocus,
  scrollRangeDown,
  scrollRangeUp,
  moveToPrevNode,
  virtualTree,
  keymap,
});
</script>
