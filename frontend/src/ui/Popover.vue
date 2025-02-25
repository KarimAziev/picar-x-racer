<template>
  <template v-if="$slots.button">
    <slot name="button" @click="toggle" :toggle="toggle" />
  </template>
  <Button v-bind="omit(['dialogProps'], props)" v-else @click="toggle">
  </Button>
  <Dialog
    closable
    dismissableMask
    closeOnEscape
    v-model:visible="visible"
    v-bind="props.dialogProps"
    @show="onShow"
    @hide="onHide"
  >
    <div ref="modalRef">
      <slot></slot>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, useTemplateRef } from "vue";
import type { DialogProps } from "primevue/dialog";
import type { ButtonProps } from "primevue/button";
import { onClickOutside } from "@vueuse/core";
import { omit } from "@/util/obj";

const emit = defineEmits(["show", "hide"]);
const visible = ref(false);
const modalRef = useTemplateRef("modalRef");

onClickOutside(modalRef, (event) => {
  console.log(event);
  visible.value = false;
});

const onShow = () => {
  emit("show");
};

const onHide = () => {
  emit("hide");
};

export type BtnProps = {
  style?: ButtonProps["style"];
  class?: ButtonProps["class"];
  label?: ButtonProps["label"];
  icon?: ButtonProps["icon"];
  iconPos?: ButtonProps["iconPos"];
  iconClass?: ButtonProps["iconClass"];
  badge?: ButtonProps["badge"];
  badgeClass?: ButtonProps["badgeClass"];
  badgeSeverity?: ButtonProps["badgeSeverity"];
  loading?: ButtonProps["loading"];
  loadingIcon?: ButtonProps["loadingIcon"];
  as?: ButtonProps["as"];
  asChild?: ButtonProps["asChild"];
  link?: ButtonProps["link"];
  severity?: ButtonProps["severity"];
  raised?: ButtonProps["raised"];
  rounded?: ButtonProps["rounded"];
  text?: ButtonProps["text"];
  outlined?: ButtonProps["outlined"];
  size?: ButtonProps["size"];
  variant?: ButtonProps["variant"];
  fluid?: ButtonProps["fluid"];
  dt?: ButtonProps["dt"];
  pt?: ButtonProps["pt"];
  ptOptions?: ButtonProps["ptOptions"];
  unstyled?: ButtonProps["unstyled"];
};

export interface Props extends BtnProps {
  disabled?: boolean;
  dialogProps?: DialogProps;
}

const props = defineProps<Props>();

const toggle = () => {
  visible.value = !visible.value;
  /**
   * popoverEl.value?.toggle(event);
   */
};
</script>
