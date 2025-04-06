<template>
  <ul>
    <li v-for="node in nodes" :key="node[keyProp]">
      <div
        @keydown.stop.prevent.enter="handleClick(node)"
        @keydown.stop.prevent.space="handleClick(node)"
        @click.stop="handleClick(node)"
        :tabindex="node.tabIdx"
        v-if="node.children"
        class="node"
        :class="{ selectable: !node.children, selected: isSelected(node) }"
      >
        <i v-if="expandedNodes.has(node[keyProp])" class="pi pi-angle-down" />

        <i v-else class="pi pi-angle-right" />
        <span v-tooltip="node[labelProp || keyProp]">
          {{ node[labelProp || keyProp] }}
        </span>
      </div>

      <div
        @keydown.stop.prevent.enter="handleClick(node)"
        @click.stop="handleClick(node)"
        @keydown.stop.prevent.space="handleClick(node)"
        :autofocus="isSelected(node)"
        :tabindex="node.tabIdx"
        v-else
        class="node selectable"
        :class="{ selected: isSelected(node) }"
      >
        <span v-tooltip="node[labelProp || keyProp]">
          {{ node[labelProp || keyProp] }}
        </span>
      </div>

      <Tree
        :keyProp="keyProp"
        :labelProp="labelProp"
        v-if="node.children && expandedNodes.has(node[keyProp])"
        :nodes="node.children"
        :modelValue="modelValue"
        @update:modelValue="emit('update:modelValue', $event)"
      />
    </li>
  </ul>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { findAncestors } from "@/util/obj";
import type { TreeNode } from "@/types/tree";

export interface Props {
  nodes: TreeNode[];
  modelValue: TreeNode | null;
  keyProp: keyof TreeNode;
  labelProp?: keyof TreeNode;
}

const props = defineProps<Props>();
const emit = defineEmits(["update:modelValue"]);

const expandedNodes = ref<Set<string>>(new Set());

const isSelected = (node: TreeNode): boolean =>
  props.modelValue
    ? props.modelValue[props.keyProp] === node[props.keyProp]
    : false;

const toggleExpand = (node: TreeNode) => {
  if (expandedNodes.value.has(node[props.keyProp])) {
    expandedNodes.value.delete(node[props.keyProp]);
  } else {
    expandedNodes.value.add(node[props.keyProp]);
  }
};

const handleClick = (node: TreeNode) => {
  if (!node.children) {
    const newSelection = isSelected(node) ? null : node;
    emit("update:modelValue", newSelection);
  } else {
    toggleExpand(node);
  }
};

const expandSelectedNodeParents = () => {
  if (props.modelValue) {
    const ancestors = findAncestors(
      props.keyProp,
      props.nodes,
      props.modelValue[props.keyProp],
    );
    ancestors.forEach((key) => expandedNodes.value.add(key));
  }
};

watch(
  () => props.modelValue,
  () => expandSelectedNodeParents(),
  { immediate: true },
);

onMounted(expandSelectedNodeParents);
</script>

<style scoped lang="scss">
ul {
  width: 250px;
  padding: 0rem 0.5rem;
}

.node {
  padding: 0.3rem 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  color: var(--p-list-option-color);
  &.selectable {
    padding-left: 1rem;
  }
  &:hover,
  &:focus {
    color: var(--p-list-option-focus-color);
    background-color: var(--p-list-option-focus-background);
  }
  &.selected {
    color: var(--p-list-option-selected-color);
    background-color: var(--p-list-option-selected-background);
    &:hover,
    &:focus {
      color: var(--p-list-option-selected-focus-color);
      background-color: var(--p-list-option-selected-focus-background);
    }
  }
}
</style>
