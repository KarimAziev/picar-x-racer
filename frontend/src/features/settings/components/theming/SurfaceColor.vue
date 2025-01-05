<template>
  <Fieldset legend="Surface Color" toggleable>
    <div class="flex flex-col gap-2 items-start">
      <div class="flex-col justify-start items-start gap-2 inline-flex pr-4">
        <span class="text-sm font-medium">Preset Colors</span>
        <div
          class="self-stretch justify-start items-start gap-2 inline-flex flex-wrap"
        >
          <button
            v-for="colorOption of surfaceOptions"
            :key="colorOption.label"
            type="button"
            :title="colorOption.label"
            @click="updateColor(colorOption.value)"
            class="outline outline-2 outline-offset-2 outline-transparent focus:ring p-0 rounded-[50%] w-5 h-5"
            :style="{
              backgroundColor: `${colorOption.bgColor}`,
              outlineColor: `${
                store.surfaceColor === colorOption.value
                  ? 'var(--p-primary-color)'
                  : ''
              }`,
            }"
          ></button>
        </div>
      </div>
      <Field label="Custom:">
        <ColorPicker
          inputId="surface-color"
          v-model="store.surfaceColor"
          @update:model-value="store.updateSurfaceColor"
        />
      </Field>
      <Button
        size="small"
        :disabled="resetDisabled"
        label="Reset"
        @click="store.resetSurface"
      />
    </div>
  </Fieldset>
</template>

<script setup lang="ts">
import ColorPicker from "primevue/colorpicker";
import Fieldset from "primevue/fieldset";
import { computed } from "vue";
import { useThemeStore } from "@/features/settings/stores";
import Field from "@/ui/Field.vue";
import { surfaceOptions } from "@/presets/surfaces";

const store = useThemeStore();

const resetDisabled = computed(() => store.isSurfaceColorDefault);

function updateColor(surfaceColor: string) {
  store.updateSurfaceColor(surfaceColor);
}
</script>
