<template>
  <Panel header="Keybindings">
    <form @submit.prevent="handleSubmit" class="m-auto justify-items-center">
      <Teleport to="#settings-footer">
        <span class="flex gap-2 justify-self-start">
          <Button
            size="small"
            label="Add Key"
            @click="addField"
            class="w-fit"
            severity="secondary"
          />
          <Button
            size="small"
            label="Save"
            type="submit"
            :disabled="isDisabled"
            class="w-fit"
          />
        </span>
      </Teleport>
      <div>
        <div
          v-for="(fieldPair, index) in fields"
          :key="index"
          class="flex gap-0.5"
        >
          <SelectField
            :field="`command-${index}`"
            fieldClassName="w-3/5 !my-0"
            inputClassName="w-full max-w-full"
            filter
            :tooltip="fieldPair[0].label"
            v-model="fieldPair[0].value"
            optionLabel="label"
            optionValue="value"
            autoFilterFocus
            :options="fieldPair[0].options"
            :disabled="fieldPair[0].props?.disabled"
            class="w-full max-w-full"
          />

          <div>
            <InputText
              v-model="fieldPair[1].value"
              :invalid="!!invalidKeys[fieldPair[1].value]"
              readonly
              @beforeinput="(event) => startRecording(event, index)"
              @focus="(event) => startRecording(event, index)"
              name="keybinding"
              class="w-full max-w-full"
            />
            <div class="text-red-500">
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
import InputText from "primevue/inputtext";
import Button from "primevue/button";
import { Panel } from "primevue";
import KeyRecorder from "@/ui/KeyRecorder.vue";
import { useSettingsStore, usePopupStore } from "@/features/settings/stores";
import { allCommandOptions } from "@/features/settings/defaultKeybindings";
import { splitKeySequence } from "@/util/keyboard-util";
import Field from "@/ui/Field.vue";
import SelectField from "@/ui/SelectField.vue";
import { diffObjectsDeep } from "@/util/obj";
import { isEmpty } from "@/util/guards";
import { ControllerActionName } from "@/features/controller/store";

const popupStore = usePopupStore();

const store = useSettingsStore();

const keyRecorderOpen = computed(() => popupStore.isKeyRecording);

const commandsToOptions = (obj: Record<string, string[] | null>): Fields => {
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
    (keybindings || []).map((k) => {
      const keyItem = makeKeybindingItem(k);
      const cmdItem = makeCommandItem(cmd);

      const pair = [cmdItem, keyItem] as FieldPair;
      return pair;
    }),
  );
  return res;
};
const fields = computed(() =>
  reactive(commandsToOptions(store.data.keybindings)),
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
const isSubmitDisabled = ref(false);

const handleSubmit = async () => {
  const errs = validateAll();
  const validFields = fields.value.filter(
    ([_, keybindingField]) => keybindingField.value.length > 0,
  );

  if (!errs.length && validFields.length > 0) {
    store.data.keybindings = pairsToConfig(validFields);
    await store.saveSettings();
  }
};

const validateAll = () => {
  const errors = validateRowsFields();
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

const isDisabled = computed(() => {
  validateAll();
  if (isSubmitDisabled.value) {
    return isSubmitDisabled.value;
  }
  const validFields = fields.value.filter(
    ([_, keybindingField]) => keybindingField.value.length > 0,
  );
  const validStoredFields = Object.entries(store.data.keybindings).reduce(
    (acc, [cmd, val]) => {
      if (val && val.length > 0) {
        acc[cmd as ControllerActionName] = val;
      }
      return acc;
    },
    {} as Partial<Record<ControllerActionName, string[] | null>>,
  );

  const data = pairsToConfig(validFields);
  const result = diffObjectsDeep(validStoredFields, data);
  return !result || isEmpty(result);
});
</script>
