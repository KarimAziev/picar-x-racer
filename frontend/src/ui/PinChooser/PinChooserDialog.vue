<template>
  <div>
    <Dialog
      v-model:visible="visible"
      header="Choose a pin"
      content-class="min-h-[35vh] max-h-[70vh] overflow-auto"
      dismissableMask
      @show="handleSelectBeforeShow"
      @hide="handleSelectBeforeHide"
    >
      <PinChooser v-bind="props" @update:model-value="updateValue" />

      <div class="text-right">
        <Button label="Close" class="p-button-text" @click="visible = false" />
      </div>
    </Dialog>

    <Field
      :message="message"
      :label="label"
      :fieldClassName="fieldClassName"
      :labelClassName="labelClassName"
      :tooltipHelp="tooltipHelp"
      :layout="layout"
      :messageClass="messageClass"
    >
      <Button
        class="w-fit min-w-32"
        outlined
        @click="visible = true"
        v-tooltip="tooltip"
        :disabled="readonly || disabled"
      >
        {{ displayLabel }}
      </Button>
    </Field>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { isNil } from "@/util/guards";

import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";

import { usePopupStore, useDeviceInfoStore } from "@/features/settings/stores";
import PinChooser from "@/ui/PinChooser/PinChooser.vue";

const deviceStore = useDeviceInfoStore();
const popupStore = usePopupStore();

const visible = ref(false);

type ModelValue = string | number | null;

export interface Props extends FieldProps {
  modelValue: ModelValue;
  label?: string;
  readonly?: boolean;
  disabled?: boolean;
  tooltip?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:modelValue", value: ModelValue): void;
}>();

const updateValue = (newValue: ModelValue) => {
  emit("update:modelValue", newValue);
  visible.value = false;
};

const handleSelectBeforeShow = () => {
  popupStore.isEscapable = false;
};

const handleSelectBeforeHide = () => {
  popupStore.isEscapable = true;
};

const displayLabel = computed(() => {
  if (isNil(props.modelValue)) {
    return "Select Pin";
  }
  const pin = deviceStore.hash.get(props.modelValue);
  if (!pin) {
    return props.modelValue;
  }

  if (pin.selectable && !pin.name.startsWith("GPIO")) {
    return `${pin.name} (GPIO${pin.gpio_number})`;
  }
  return pin.name;
});

onMounted(deviceStore.fetchDataOnce);
</script>
