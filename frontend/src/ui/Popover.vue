<template>
  <template v-if="$slots.button">
    <slot name="button" @click="toggle" :toggle="toggle" />
  </template>
  <Button v-bind="omit(['popoverProps'], props)" v-else @click="toggle">
  </Button>
  <Popover
    ref="popoverEl"
    v-bind="props.popoverProps"
    @show="onShow"
    @hide="onHide"
  >
    <slot></slot>
  </Popover>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Popover } from "primevue";
import type { PopoverProps, PopoverMethods } from "primevue/popover";
import type { ButtonProps } from "primevue/button";
import { omit } from "@/util/obj";

const emit = defineEmits(["show", "hide"]);

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
  popoverProps?: PopoverProps;
}

const props = defineProps<Props>();

const popoverEl = ref<PopoverMethods>();

const toggle = (event: Event) => {
  popoverEl.value?.toggle(event);
};
</script>
