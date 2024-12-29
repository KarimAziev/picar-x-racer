<template>
  <ul>
    <li v-for="node in nodes" :key="node.key">
      <div
        @keydown.stop.prevent.enter="handleClick(node)"
        @keydown.stop.prevent.space="handleClick(node)"
        @click.stop="handleClick(node)"
        :tabindex="node.tabIdx"
        v-if="node.children"
        class="node"
        :class="{ selectable: !node.children, selected: isSelected(node) }"
      >
        <i v-if="expandedNodes.has(node.key)" class="pi pi-angle-down" />

        <i v-else class="pi pi-angle-right" />
        <span v-tooltip="node.label">
          {{ node.label }}
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
        <span v-tooltip="node.label">
          {{ node.label }}
        </span>
      </div>

      <Tree
        v-if="node.children && expandedNodes.has(node.key)"
        :nodes="node.children"
        :modelValue="modelValue"
        @update:modelValue="emit('update:modelValue', $event)"
      />
    </li>
  </ul>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from "vue";

export interface TreeNode {
  key: string;
  label?: string;
  children?: TreeNode[];
  tabIdx?: number;
  [key: string]: any;
}

const props = defineProps<{
  nodes: TreeNode[];
  modelValue: TreeNode | null;
}>();

const emit = defineEmits(["update:modelValue"]);

const expandedNodes = ref<Set<string>>(new Set());

const isSelected = (node: TreeNode): boolean => {
  return props.modelValue?.key === node.key;
};

const toggleExpand = (node: TreeNode) => {
  if (expandedNodes.value.has(node.key)) {
    expandedNodes.value.delete(node.key);
  } else {
    expandedNodes.value.add(node.key);
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

const findAncestors = (
  nodes: TreeNode[],
  targetKey: string,
  currentPath: string[] = [],
): string[] => {
  for (const node of nodes) {
    const path = [...currentPath, node.key];
    if (node.key === targetKey) {
      return path.slice(0, -1);
    }
    if (node.children) {
      const result = findAncestors(node.children, targetKey, path);
      if (result.length) return result;
    }
  }
  return [];
};

const expandSelectedNodeParents = () => {
  if (props.modelValue) {
    const ancestors = findAncestors(props.nodes, props.modelValue.key);
    ancestors.forEach((key) => expandedNodes.value.add(key));
  }
};

watch(
  () => props.modelValue,
  () => expandSelectedNodeParents(),
  { immediate: true },
);

onMounted(() => {
  expandSelectedNodeParents();
});
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
