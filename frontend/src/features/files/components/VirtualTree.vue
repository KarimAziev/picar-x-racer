<template>
  <VirtualScroller
    ref="virtualScoller"
    :items="flatNodes"
    v-bind="omit(['nodes', 'keyProp', 'labelProp', 'rowClass'], props)"
  >
    <template v-slot:item="{ item: node, options }">
      <template v-if="$slots.row">
        <slot
          name="row"
          :tabindex="options.index"
          :node="node"
          :options="options"
        />
      </template>

      <RowWrapper
        v-else
        :tabindex="options.index"
        :level="node.level"
        :path="node[keyProp]"
        v-bind="node"
        class="flex items-center gap-1"
        :class="rowClass"
      >
        <button
          v-if="node.children"
          @click="toggleExpand(node)"
          :class="`pi rounded-md bg-transparent transition-opacity duration-300 ease-in-out hover:opacity-70 hover:bg-button-text-primary-hover-background focus:opacity-70 focus:outline-none pi-chevron-${expandedNodes.has(node[keyProp]) ? 'down' : 'right'}`"
        />
        <div v-else class="ml-4" />
        <template v-if="$slots.cells">
          <slot name="cells" :node="node" :tabindex="options.index" />
        </template>
        <template v-else>
          <span v-tooltip="node[labelProp || keyProp]">
            {{ node[labelProp || keyProp] }}
          </span>
        </template>
      </RowWrapper>
    </template>
    <slot></slot>
  </VirtualScroller>
</template>

<script setup lang="ts">
import { computed, inject, useTemplateRef } from "vue";
import type { Ref } from "vue";
import type { VirtualScrollerProps } from "primevue/virtualscroller";
import type { TreeNode } from "@/types/tree";
import { omit } from "@/util/obj";
import RowWrapper from "@/features/files/components/RowWrapper.vue";

const virtualScoller = useTemplateRef("virtualScoller");

export interface Props extends Omit<VirtualScrollerProps, "items"> {
  nodes: TreeNode[];
  keyProp: keyof TreeNode;
  itemSize: number;
  labelProp?: keyof TreeNode;
  rowClass?: string;
}

const props = withDefaults(defineProps<Props>(), {});

const emit = defineEmits(["toggle:expand"]);

const expandedNodes = inject<Ref<Set<string>>>("expandedNodes");

if (!expandedNodes) {
  throw new Error("Expanded nodes and marked nodes must be provided!");
}

const flatNodes = computed(() => {
  const result: (TreeNode & { level: number })[] = [];

  const flatten = (nodes: TreeNode[], level: number) => {
    nodes.forEach((node) => {
      result.push({ ...node, level });

      if (node.children && expandedNodes.value.has(node[props.keyProp])) {
        flatten(node.children, level + 1);
      }
    });
  };

  flatten(props.nodes, 0);

  return result;
});

const toggleExpand = (node: TreeNode & { level: number }) => {
  if (expandedNodes.value.has(node[props.keyProp])) {
    expandedNodes.value.delete(node[props.keyProp]);
  } else {
    expandedNodes.value.add(node[props.keyProp]);
  }
  emit("toggle:expand", node);
};

defineExpose({ virtualScoller, toggleExpand, flatNodes });
</script>
