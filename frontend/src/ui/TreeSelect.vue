<template>
  <button
    :disabled="disabled || loading"
    ref="btnRef"
    class="btn tree-btn pl-3"
    type="button"
    @keydown.stop.prevent.escape="handleClose"
    @click="toggle"
  >
    <span
      v-if="modelValue?.label"
      class="btn-label"
      v-tooltip="modelValue?.label"
      >{{ modelValue?.label }}</span
    >
    <span v-else class="placeholder">{{ modelValue?.label }}</span>
    <i class="pi pi-angle-down pt-1 md:pt-1.5 pr-2" />
  </button>

  <Popover ref="op" closeOnEscape @keydown.stop.prevent.escape="handleClose">
    <ScrollPanel class="wrapper">
      <Tree
        :modelValue="modelValue"
        :nodes="nodes"
        @update:model-value="handleUpdate"
      />
    </ScrollPanel>
  </Popover>
</template>

<script setup lang="ts">
import { ref } from "vue";
import Popover from "primevue/popover";
import Tree from "@/ui/Tree.vue";
import type { TreeNode } from "@/ui/Tree.vue";

defineProps<{
  nodes: TreeNode[];
  modelValue: TreeNode | null;
  loading?: boolean;
  disabled?: boolean;
}>();

const op = ref<InstanceType<typeof Popover>>();
const btnRef = ref<HTMLButtonElement>();

const toggle = (event: MouseEvent) => {
  op.value?.toggle(event);
};

const handleClose = () => {
  op.value?.hide();
};

const emit = defineEmits(["update:modelValue"]);

const handleUpdate = (node: TreeNode) => {
  emit("update:modelValue", node);
  handleClose();
};
</script>
<style scoped lang="scss">
.btn {
  justify-content: space-between;
  background-color: var(--p-form-field-background);
  border: 1px solid var(--p-form-field-border-color);
  outline: none;
  cursor: pointer;
  border-radius: var(--p-form-field-border-radius);
  flex: auto;

  font-size: inherit;

  .btn-label {
    width: 100%;
    text-align: left;
  }

  i {
    color: var(--p-form-field-icon-color);
  }
  &:disabled {
    cursor: default;
  }
  &:focus {
    border-color: var(--p-form-field-focus-border-color);
    outline: none;
  }
  &:hover {
    background-color: var(--p-form-field-background);
    border-color: var(--p-form-field-hover-border-color);
  }
  &:disabled {
    i {
      color: var(--p-form-field-placeholder-color);
    }
  }
}
.placeholder {
  color: var(--p-form-field-placeholder-color);
}
.btn-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--p-form-field-color);
}
.wrapper {
  max-height: 300px;
}
:deep(.p-scrollpanel-content) {
  max-height: 300px;
}
</style>
