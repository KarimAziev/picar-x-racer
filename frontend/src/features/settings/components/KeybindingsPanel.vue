<template>
  <Panel header="Keybindings">
    <form
      @submit.prevent="handleSubmit"
      @reset.prevent="handleReset"
      class="keybindings-form"
    >
      <div>
        <div v-for="(fieldPair, index) in fields" :key="index" class="row">
          <div class="field cmd-field">
            <Select
              filter
              :v-tooltip="fieldPair[0].label"
              v-model="fieldPair[0].value"
              optionLabel="label"
              size="small"
              optionValue="value"
              :options="fieldPair[0].options"
              :disabled="fieldPair[0].props?.disabled"
              class="select"
            />
            <div class="error-box"></div>
          </div>
          <div class="field key-field">
            <InputText
              v-model="fieldPair[1].value"
              :invalid="!!invalidKeys[fieldPair[1].value]"
              readonly
              @beforeinput="(event) => startRecording(event, index)"
              @focus="(event) => startRecording(event, index)"
              name="keybinding"
              class="input-text"
            />
            <div class="error-box">
              {{ invalidKeys[fieldPair[1].value] }}
            </div>
          </div>
          <div>
            <Button
              icon="pi pi-times"
              class="p-button-rounded p-button-danger p-button-text"
              @click="removeField(index)"
            />
          </div>
        </div>
      </div>

      <span class="form-footer">
        <Button
          size="small"
          label="Add Key"
          @click="addField"
          class="p-button-sm"
        />
        <Button
          size="small"
          label="Save"
          type="submit"
          :disabled="isSubmitDisabled"
          class="p-button-sm"
        />
        <Button
          label="Reset to defaults"
          type="reset"
          size="small"
          class="p-button-sm p-button-secondary"
        />
      </span>
    </form>
    <KeyRecorder
      v-if="keyRecorderOpen"
      :onSubmit="handleKeySubmit"
      :onCancel="handleKeyCancel"
      :validate="validateKey"
    />
  </Panel>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from "vue";
import Panel from "@/ui/Panel.vue";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Button from "primevue/button";
import KeyRecorder from "./KeyRecorder.vue";
import { useSettingsStore, usePopupStore } from "@/features/settings/stores";
import { allCommandOptions } from "@/features/settings/defaultKeybindings";
import { splitKeySequence } from "@/util/keyboard-util";

const popupStore = usePopupStore();

const store = useSettingsStore();
const originalKeys = computed(() => store.settings.keybindings);
const keyRecorderOpen = computed(() => popupStore.isKeyRecording);

const commandsToOptions = (obj: Record<string, string[]>): Fields => {
  const makeKeybindingItem = (key: string): KeybindingField => ({
    label: "Keybinding",
    name: "keybinding",
    value: key,
  });
  const makeCommandItem = (value: string): CommandOptionField => ({
    label: "Command",
    name: "command",
    value,
    options: [...allCommandOptions],
  });

  const commandOrder = new Map<string, number>(
    allCommandOptions.map((option, index) => [option.value, index]),
  );

  const sortedEntries = Object.entries(obj).sort(
    ([cmdA], [cmdB]) =>
      (commandOrder.get(cmdA) ?? Infinity) -
      (commandOrder.get(cmdB) ?? Infinity),
  );

  const res = sortedEntries.flatMap(([cmd, keybindings]) =>
    keybindings.map((k) => {
      const keyItem = makeKeybindingItem(k);
      const cmdItem = makeCommandItem(cmd);

      const pair = [cmdItem, keyItem] as FieldPair;
      return pair;
    }),
  );
  return res;
};
const fields = computed(() =>
  reactive(commandsToOptions(store.settings.keybindings)),
);

const invalidKeys = computed(() =>
  fields.value.reduce(
    (acc, field, idx) => {
      const key = field[1].value;

      const error = validateKey(key, idx);

      if (error) {
        acc[key] = error;
      }
      return acc;
    },
    {} as Record<string, string>,
  ),
);

export interface Option {
  label: string;
  value: string;
}

export interface KeybindingField<
  K extends keyof HTMLElementTagNameMap = "input",
> {
  name: string;
  value: string;
  label: string;
  props?: {
    [P in keyof HTMLElementTagNameMap[K] as P]?: HTMLElementTagNameMap[K][P];
  };
}

export interface CommandOptionField extends KeybindingField<"select"> {
  options: Option[];
  value: Option["value"];
}

export type Field = CommandOptionField | KeybindingField;

export type FieldPair = [CommandOptionField, KeybindingField];
export type Fields = FieldPair[];
export interface DynamicFormParams {
  onSave?: (fields: Fields) => void;
  onReset?: () => { fields: Fields };
}

const currentRecordingIndex = ref<number | null>(null);

const pairsToConfig = (fields: Fields) =>
  fields.reduce(
    (acc, [cmdItem, keyItem]) => {
      if (keyItem.value && keyItem.value.length > 0) {
        acc[cmdItem.value] = acc[cmdItem.value] || [];
        acc[cmdItem.value].push(keyItem.value);
      }

      return acc;
    },
    {} as Record<string, string[]>,
  );

const addField = () => {
  fields.value.push([
    {
      label: "Command",
      name: "command",
      value: "forward",
      options: [...allCommandOptions],
      props: undefined,
    },
    {
      label: "Keybinding",
      name: "keybinding",
      value: "",
      props: undefined,
    },
  ]);
};

const removeField = (index: number) => {
  fields.value.splice(index, 1);
};

const validateKey = (key: string, idx: number) => {
  if (key.length === 0) {
    return "Required";
  }

  const allKeys = fields.value.reduce(
    (acc, [cmd, keybindingField], index) => {
      if (
        idx !== index &&
        keybindingField.value &&
        keybindingField.value.length > 0
      ) {
        const found = allCommandOptions.find((c) => c.value === cmd.value);
        if (found) {
          acc[keybindingField.value] = found.label;
        }
      }
      return acc;
    },
    {} as Record<string, string>,
  );

  if (allKeys[key]) {
    return `${key} is already used in ${allKeys[key]}`;
  }
  const splittedKey = splitKeySequence(key);
  const splittedKeyLen = splittedKey.length;

  const commonPrefix = Object.keys(allKeys).find((v) => {
    const splitted = splitKeySequence(v);
    const len = Math.min(splitted.length, splittedKeyLen);
    return splitted.slice(0, len).every((k, i) => k === splittedKey[i]);
  });

  if (commonPrefix) {
    return `The prefix ${commonPrefix} conflicts with an existing key`;
  }

  return false;
};

const startRecording = (event: Event, index: number) => {
  event?.preventDefault();
  currentRecordingIndex.value = index;
  popupStore.isKeyRecording = true;
};

const handleKeySubmit = (keytext: string) => {
  if (currentRecordingIndex.value !== null) {
    fields.value[currentRecordingIndex.value][1].value = keytext;
  }
  popupStore.isKeyRecording = false;
  validateAll();
};

const handleKeyCancel = () => {
  popupStore.isKeyRecording = false;
};

const handleSubmit = async () => {
  const errs = validateAll();
  const validFields = fields.value.filter(
    ([_, keybindingField]) => keybindingField.value.length > 0,
  );

  if (!errs.length && validFields.length > 0) {
    store.settings.keybindings = pairsToConfig(validFields);
    await store.saveSettings();
  }
};

const handleReset = () => {
  store.settings.keybindings = originalKeys.value;
};

const validateAll = () => {
  const errors = validateRowsFields();
  console.log("errors", errors);
  isSubmitDisabled.value = !!errors.length;
  return errors;
};

const validateRowsFields = () => {
  const errors: [string, string][] = [];

  fields.value.forEach((_, idx) => {
    const err = validateKey(fields.value[idx][1].value, idx);
    if (err) {
      errors.push([fields.value[idx][1].value, err]);
    }
  });

  return errors;
};

const isSubmitDisabled = ref(false);
</script>

<style scoped lang="scss">
.keybindings-form {
  margin: auto;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  justify-items: center;
}

.row {
  display: flex;
  gap: 0.125rem;
  .select,
  .input-text,
  .p-button-sm {
    max-width: 100%;
    min-width: 100%;
    width: 100%;
  }
}

.select,
.input-text {
  height: 30px;
  max-width: 100%;
  width: 100%;
}

.p-button-sm {
  width: fit-content;
  height: 30px;
}

.cmd-field {
  width: 60%;
}

.key-field {
  width: 30%;
}

.error-box {
  color: var(--color-red);
  width: 10%;
}

.form-footer {
  display: flex;
  justify-content: flex-start;
  gap: 1rem;
  margin-top: 2rem;
}

:deep(.p-select-label) {
  padding: 0.15rem 0.4rem;

  @media (min-width: 640px) {
    padding: 0.3rem 0.7rem;
  }

  @media (min-width: 1200px) {
    padding: 0.4rem 0.7rem;
  }
}
</style>
