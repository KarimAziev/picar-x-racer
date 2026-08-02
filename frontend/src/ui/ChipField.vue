<template>
  <Field
    :message="msg || message"
    :label="label"
    :fieldClassName="fieldClassName"
    :labelClassName="labelClassName"
    :tooltipHelp="tooltipHelp"
    :layout="layout"
    :messageClass="messageClass"
  >
    <TextInput
      ref="inputRef"
      :invalid="!!msg"
      :id="field"
      :pt="{ input: { id: field } }"
      @focus="handleFocus"
      @click="handleFocus"
      :class="inputClass"
      :placeholder="placeholder"
      v-model="inputValue"
      v-bind="omit(['modelValue', 'suggestions'], { ...props, ...otherAttrs })"
      @update:model-value="handleResetMsg"
      v-tooltip="tooltip"
      :fluid="fluid"
      :disabled="disabled || readonly"
    />
  </Field>
  <Popover
    ref="popoverRef"
    @show="handleSelectBeforeShow"
    @hide="handleSelectBeforeHide"
  >
    <div
      class="grid w-[min(36rem,calc(100vw-2rem))] grid-cols-2 divide-x divide-[var(--p-content-border-color)]"
    >
      <section class="flex min-w-0 flex-col pr-2">
        <div class="flex min-h-8 items-center justify-between gap-2 px-2">
          <span class="text-sm font-bold">Suggestions</span>
          <span class="text-xs opacity-60">
            {{ filteredSuggestions.length }}
          </span>
        </div>
        <div ref="suggestionListRef" class="max-h-64 overflow-y-auto">
          <button
            v-for="(value, index) in filteredSuggestions"
            :key="value"
            type="button"
            :data-suggestion-index="index"
            class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-button-text-primary-hover-background focus:outline-none focus:ring-2 focus:ring-current"
            :aria-label="`Add ${value}`"
            @mousedown.prevent
            @click="addValue(value)"
          >
            <span class="min-w-0 truncate">{{ value }}</span>
            <span
              v-if="isCustomSuggestion(value)"
              class="ml-auto shrink-0 text-xs opacity-60"
            >
              custom
            </span>
          </button>
          <p
            v-if="filteredSuggestions.length === 0"
            class="px-2 py-3 text-sm opacity-60"
          >
            No matching suggestions
          </p>
        </div>
      </section>

      <section class="flex min-w-0 flex-col pl-2">
        <div class="flex min-h-8 items-center justify-between gap-2 px-2">
          <span class="text-sm font-bold">
            Selected ({{ selectedValues.length }})
          </span>
          <button
            v-if="selectedValues.length"
            type="button"
            class="rounded px-1.5 py-0.5 text-xs text-red-400 hover:bg-button-text-primary-hover-background focus:outline-none focus:ring-2 focus:ring-current"
            @mousedown.prevent
            @click="clearValues"
          >
            Clear all
          </button>
        </div>
        <div class="max-h-64 overflow-y-auto">
          <button
            v-for="value in selectedValues"
            :key="value"
            type="button"
            class="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left hover:bg-button-text-primary-hover-background focus:outline-none focus:ring-2 focus:ring-current"
            :aria-label="`Remove ${value}`"
            @mousedown.prevent
            @click="removeValue(value)"
          >
            <span class="min-w-0 truncate">{{ value }}</span>
            <i
              class="pi pi-times shrink-0 text-xs text-red-400"
              aria-hidden="true"
            />
          </button>
          <p
            v-if="selectedValues.length === 0"
            class="px-2 py-3 text-sm opacity-60"
          >
            No selected values
          </p>
        </div>
      </section>
    </div>
  </Popover>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onUnmounted,
  ref,
  useAttrs,
  useTemplateRef,
  watch,
} from "vue";
import TextInput from "primevue/inputtext";
import type { InputTextProps } from "primevue/inputtext";
import type { PopoverMethods } from "primevue/popover";
import Field from "@/ui/Field.vue";
import type { Props as FieldProps } from "@/ui/Field.vue";
import { omit } from "@/util/obj";
import { usePopupStore } from "@/features/settings/stores";
import { filterChipSuggestions } from "@/ui/chipFieldSuggestions";
import { formatKeyEventItem } from "@/util/keyboard-util";
import { isNumber } from "@/util/guards";

defineOptions({ inheritAttrs: false });

export interface Props extends FieldProps {
  modelValue: string[] | null;
  label?: string;
  field?: string;
  inputClass?: string;
  readonly?: boolean;
  disabled?: boolean;
  size?: "small" | "large" | undefined;
  tooltip?: string;
  suggestions?: string[];
  fluid?: boolean;
  limit?: number;
}

const popoverRef = ref<PopoverMethods>();
const inputRef = useTemplateRef<
  InstanceType<typeof TextInput> & { $el: HTMLInputElement }
>("inputRef");
const suggestionListRef = useTemplateRef("suggestionListRef");
const props = defineProps<Props>();
const otherAttrs: InputTextProps = useAttrs();
const placeholder = computed(() => {
  if (!currentValue.value || !currentValue.value.length) {
    return "All";
  }
  const valLen = currentValue.value.length;
  return valLen === 1 ? `${currentValue.value.join(", ")}` : `${valLen} labels`;
});

const currentValue = ref(props.modelValue);
const selectedValues = computed(() => currentValue.value || []);
const msg = ref<string | null>(null);
const inputValue = ref("");
const suppressNextFocus = ref(false);

const filteredSuggestions = computed(() =>
  filterChipSuggestions(
    props.suggestions || [],
    selectedValues.value,
    inputValue.value,
    props.limit || (props.suggestions || []).length,
  ),
);
const normalizedSuggestions = computed(() => {
  const items = (props.suggestions || []).map((value) =>
    value.toLocaleLowerCase(),
  );

  return new Set(items);
});

const handleFocus = (ev: Event) => {
  if (suppressNextFocus.value) {
    suppressNextFocus.value = false;
    return;
  }

  if (!props.disabled && !props.readonly) {
    handleSelectBeforeShow();
    popoverRef.value?.show(ev);
  }
};

const popupStore = usePopupStore();
const handleSelectBeforeShow = () => {
  popupStore.isEscapable = false;
  addKeyEventListeners();
};

const handleSelectBeforeHide = () => {
  removeKeyEventListeners();
  popupStore.isEscapable = true;
};
onUnmounted(handleSelectBeforeHide);

const handleResetMsg = () => {
  msg.value = null;
};
watch(
  () => props.modelValue,
  (newVal) => {
    currentValue.value = newVal;
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string[]];
}>();

const normalizeValue = (value: string) => value.toLocaleLowerCase();

const addValue = (value: string) => {
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return;
  }

  const normalizedValue = normalizeValue(trimmedValue);
  if (
    selectedValues.value.some(
      (selectedValue) => normalizeValue(selectedValue) === normalizedValue,
    )
  ) {
    msg.value = "Already selected";
    return;
  }

  const nextValue = [...selectedValues.value, trimmedValue];
  currentValue.value = nextValue;
  inputValue.value = "";
  msg.value = null;
  emit("update:modelValue", nextValue);
};

const handleKeyEnter = () => {
  const trimmedValue = inputValue.value.trim();
  const exactSuggestion = (props.suggestions || []).find(
    (suggestion) => normalizeValue(suggestion) === normalizeValue(trimmedValue),
  );

  addValue(exactSuggestion || trimmedValue);
};

const getCurrentSuggestionIndex = () => {
  const attrValue = document.activeElement?.getAttribute(
    "data-suggestion-index",
  );

  if (attrValue !== null && attrValue !== undefined) {
    return Number(attrValue);
  }
};

const moveFocus = (newIndex: number) => {
  nextTick(() => {
    const suggestion = suggestionListRef.value?.querySelector<HTMLElement>(
      `[data-suggestion-index="${newIndex}"]`,
    );

    if (suggestion) {
      suggestion.focus();
      suggestion.scrollIntoView?.({ block: "nearest" });
    }
  });
};

const moveToNextSuggestion = () => {
  const lastIndex = filteredSuggestions.value.length - 1;
  if (lastIndex < 0) {
    return;
  }

  const currentIndex = getCurrentSuggestionIndex();
  moveFocus(isNumber(currentIndex) ? Math.min(currentIndex + 1, lastIndex) : 0);
};

const moveToPrevSuggestion = () => {
  if (filteredSuggestions.value.length === 0) {
    return;
  }

  const currentIndex = getCurrentSuggestionIndex();
  moveFocus(isNumber(currentIndex) ? Math.max(currentIndex - 1, 0) : 0);
};

const getSuggestionPageSize = () => {
  const list = suggestionListRef.value;
  const firstSuggestion = list?.querySelector<HTMLElement>(
    "[data-suggestion-index]",
  );

  if (!list || !firstSuggestion || firstSuggestion.offsetHeight === 0) {
    return filteredSuggestions.value.length;
  }

  return Math.max(
    1,
    Math.floor(list.clientHeight / firstSuggestion.offsetHeight),
  );
};

const scrollSuggestionsDown = () => {
  const lastIndex = filteredSuggestions.value.length - 1;
  if (lastIndex < 0) {
    return;
  }

  const currentIndex = getCurrentSuggestionIndex();
  const nextIndex = isNumber(currentIndex)
    ? Math.min(currentIndex + getSuggestionPageSize(), lastIndex)
    : Math.min(getSuggestionPageSize() - 1, lastIndex);
  moveFocus(nextIndex);
};

const scrollSuggestionsUp = () => {
  if (filteredSuggestions.value.length === 0) {
    return;
  }

  const currentIndex = getCurrentSuggestionIndex();
  const nextIndex = isNumber(currentIndex)
    ? Math.max(currentIndex - getSuggestionPageSize(), 0)
    : 0;
  moveFocus(nextIndex);
};

const selectFocusedSuggestion = () => {
  const currentIndex = getCurrentSuggestionIndex();
  if (isNumber(currentIndex)) {
    const suggestion = filteredSuggestions.value[currentIndex];
    if (suggestion !== undefined) {
      addValue(suggestion);
      nextTick(() => inputRef.value?.$el.focus());
      return true;
    }
  }

  if (document.activeElement === inputRef.value?.$el) {
    handleKeyEnter();
    return true;
  }

  return false;
};

const handleClose = () => {
  const input = inputRef.value?.$el;
  suppressNextFocus.value = document.activeElement !== input;
  handleSelectBeforeHide();
  popoverRef.value?.hide();
  nextTick(() => input?.focus());
};

const keymap: Record<string, (event: KeyboardEvent) => boolean | void> = {
  "Ctrl-n": moveToNextSuggestion,
  ArrowDown: moveToNextSuggestion,
  "Ctrl-p": moveToPrevSuggestion,
  ArrowUp: moveToPrevSuggestion,
  Enter: selectFocusedSuggestion,
  "Ctrl-v": scrollSuggestionsDown,
  "Alt-v": scrollSuggestionsUp,
  Escape: handleClose,
  "Ctrl-g": handleClose,
};

const handleListKeydown = (event: KeyboardEvent) => {
  const handler = keymap[formatKeyEventItem(event)];
  if (!handler) {
    return;
  }

  const handled = handler(event);
  if (handled === false) {
    return;
  }

  event.stopPropagation();
  event.preventDefault();
};

function addKeyEventListeners() {
  window.addEventListener("keydown", handleListKeydown);
}

function removeKeyEventListeners() {
  window.removeEventListener("keydown", handleListKeydown);
}

const removeValue = (removedValue: string) => {
  const nextValue = selectedValues.value.filter(
    (value) => value !== removedValue,
  );
  currentValue.value = nextValue;
  msg.value = null;
  emit("update:modelValue", nextValue);
};

const clearValues = () => {
  currentValue.value = [];
  msg.value = null;
  emit("update:modelValue", []);
};

const isCustomSuggestion = (value: string) =>
  !normalizedSuggestions.value.has(normalizeValue(value));
</script>
<style scoped lang="scss">
.p-inputtext::placeholder {
  color: var(--p-inputtext-color);
}
</style>
