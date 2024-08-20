<template>
  <Panel header="Keybindings">
    <form
      @submit.prevent="handleSubmit"
      @reset.prevent="handleReset"
      class="keybindings-form"
    >
      <div class="rows">
        <div v-for="(fieldPair, index) in fields" :key="index" class="form-row">
          <div class="field">
            <Select
              v-model="fieldPair[0].value"
              optionLabel="label"
              optionValue="value"
              :options="fieldPair[0].options"
              :disabled="fieldPair[0].props?.disabled"
              class="select"
            />
            <div class="error-box"></div>
          </div>
          <div class="field">
            <InputText
              v-model="fieldPair[1].value"
              @beforeinput="(event) => startRecording(event, index)"
              name="keybinding"
              class="input-text"
            />
            <div class="error-box"></div>
          </div>
          <Button
            icon="pi pi-times"
            class="p-button-rounded p-button-danger p-button-text"
            @click="removeField(index)"
          />
        </div>
      </div>
      <div class="form-footer">
        <Button label="Add Key" @click="addField" class="p-button-sm" />
        <Button
          label="Save"
          type="submit"
          :disabled="isSubmitDisabled"
          class="p-button-sm"
        />
        <Button
          label="Reset to defaults"
          type="reset"
          class="p-button-sm p-button-secondary"
        />
      </div>
    </form>
    <KeyRecorder
      v-if="showRecorder"
      :onSubmit="handleKeySubmit"
      :onCancel="handleKeyCancel"
      :validate="validateKey"
    />
  </Panel>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from "vue";
import Panel from "primevue/panel";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Button from "primevue/button";
import KeyRecorder from "./KeyRecorder.vue";
import { useSettingsStore } from "@/features/settings/stores";
import {
  defaultKeybindinds,
  allCommandOptions,
} from "@/features/settings/defaultKeybindings";

const store = useSettingsStore();

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

  const res = Object.entries(obj).flatMap(([cmd, keybindings]) =>
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

const showRecorder = ref(false);
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
    (acc, [_, keybindingField], index) => {
      if (
        idx !== index &&
        keybindingField.value &&
        keybindingField.value.length > 0
      ) {
        acc[keybindingField.value] = true;
      }
      return acc;
    },
    {} as Record<string, boolean>,
  );

  if (allKeys[key]) {
    return `<b>${key}</b> is already used`;
  }

  const commonPrefix = Object.keys(allKeys).find((v) => key.startsWith(v));

  if (commonPrefix) {
    return `The prefix <b>${commonPrefix}</b> conflicts with an existing key`;
  }

  return false;
};

const startRecording = (event: Event, index: number) => {
  event?.preventDefault();
  currentRecordingIndex.value = index;
  showRecorder.value = true;
};

const handleKeySubmit = (keytext: string) => {
  if (currentRecordingIndex.value !== null) {
    fields.value[currentRecordingIndex.value][1].value = keytext;
  }
  showRecorder.value = false;
  validateAll();
};

const handleKeyCancel = () => {
  showRecorder.value = false;
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

const handleReset = async () => {
  store.settings.keybindings = { ...defaultKeybindinds };
  await store.saveSettings();
};

const validateAll = () => {
  const errors = validateRowsFields();
  isSubmitDisabled.value = !!errors.length;
  return errors;
};

const validateRowsFields = () => {
  const errors: string[] = [];

  fields.value.forEach((_, idx) => {
    const err = validateKey(fields.value[idx][1].value, idx);
    if (err) {
      errors.push(err);
    }
  });

  return errors;
};

const isSubmitDisabled = ref(false);
</script>

<style scoped lang="scss">
.keybindings-form {
  min-width: 820px;
  max-width: 1200px;
  margin: auto;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  justify-items: center;
}
.select,
.input-text {
  width: 70%;
}
.rows {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.form-row {
  display: flex;
  align-items: center;
  justify-items: flex-end;
  margin-bottom: 1rem;
}

.field {
  width: 50%;
}

.error-box {
  color: red;
}

.form-footer {
  display: flex;
  justify-content: flex-start;
  gap: 1rem;
  margin-top: 2rem;
}
</style>
