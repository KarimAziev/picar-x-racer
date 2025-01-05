<template>
  <Fieldset toggleable legend="Primary Color">
    <div class="flex flex-col gap-2 items-start">
      <div class="flex-col justify-start items-start gap-2 inline-flex pr-4">
        <span class="text-sm font-medium">Preset Colors</span>
        <div
          class="self-stretch justify-start items-start gap-2 inline-flex flex-wrap"
        >
          <button
            v-for="colorOption of colorOptions"
            :key="colorOption.label"
            type="button"
            :title="startCase(colorOption.label)"
            @click="updateColor(colorOption.value)"
            class="outline outline-2 outline-offset-2 outline-transparent cursor-pointer p-0 rounded-[50%] w-5 h-5 focus:ring"
            :style="{
              backgroundColor: `${colorOption.value}`,
              outlineColor: `${
                store.primaryColor === colorOption.value
                  ? 'var(--p-primary-color)'
                  : ''
              }`,
            }"
          ></button>
        </div>
      </div>
      <Field label="Custom:">
        <ColorPicker
          inputId="primary-color"
          v-model="store.primaryColor"
          @update:model-value="store.updatePrimaryColor"
        />
      </Field>
      <Button
        size="small"
        :disabled="resetDisabled"
        label="Reset"
        @click="store.resetPrimaryColor"
      />
    </div>
  </Fieldset>
</template>

<script setup lang="ts">
import ColorPicker from "primevue/colorpicker";
import Fieldset from "primevue/fieldset";
import { computed } from "vue";
import { colorOptions } from "@/features/settings/components/theming/colors";
import { useThemeStore } from "@/features/settings/stores";
import Field from "@/ui/Field.vue";
import { startCase } from "@/util/str";

const store = useThemeStore();

const resetDisabled = computed(() => store.isPrimaryColorDefault);

function updateColor(newColor: string) {
  store.updatePrimaryColor(newColor);
}
</script>
