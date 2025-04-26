<template>
  <div v-if="isObjectSchema && resolvedSchema">
    <Fieldset
      :legend="startCase(resolvedSchema.title || keyName)"
      toggleable
      :collapsed="collapsed"
      :id="idPrefix"
    >
      <div
        v-for="(propSchema, propName) in resolvedSchema.properties"
        :key="propName"
      >
        <RecursiveField
          :idPrefix="`${idPrefix}-${[selectedOption, ...path].join('-')}`"
          :key="[selectedOption, ...path].join('-')"
          :schema="propSchema"
          :model="model"
          :path="[...path, propName]"
          :defs="defs"
        />
      </div>
    </Fieldset>
  </div>

  <div v-else-if="isArraySchema && resolvedSchema">
    <Fieldset
      :legend="startCase(resolvedSchema.title || keyName)"
      toggleable
      :id="idPrefix"
      :collapsed="collapsed"
    >
      <div v-for="(item, index) in localValue" :key="index" class="mb-4">
        <div class="grid grid-cols-[80%_20%] gap-2">
          <SelectField
            :label="resolvedSchema.title || keyName"
            :options="anyOfOptions"
            v-model="item._optionSelected"
            :tooltipHelp="tooltipHelp"
          />
          <Button
            @click="handleRemoveArrayItem(index as number)"
            icon="pi pi-times"
            class="p-button-rounded p-button-danger p-button-text"
          />
        </div>
        <RecursiveField
          :collapsed="false"
          :idPrefix="`${idPrefix}-${[item._optionSelected, ...path, index].join('-')}`"
          :key="[item._optionSelected, ...path, index].join('-')"
          :schema="
            (resolvedSchema.items?.anyOf
              ? resolveRef(resolvedSchema.items?.anyOf[item._optionSelected])
              : resolvedSchema.items) || null
          "
          :model="model"
          :path="[...path, index]"
          :defs="defs"
        />
      </div>
      <div class="py-2">
        <Button
          size="small"
          icon="pi pi-plus"
          label="Add Item"
          @click="handleAddListItem"
          class="w-fit"
          severity="secondary"
        />
      </div>
    </Fieldset>
  </div>

  <SelectField
    v-else-if="enumOptions"
    :label="startCase(resolvedSchema?.title || keyName)"
    :options="enumOptions"
    v-model="localValue"
    :tooltipHelp="tooltipHelp"
  />

  <component
    v-else-if="comp"
    :is="comp"
    v-bind="compProps"
    v-model="localValue"
    :label="resolvedSchema.title || keyName"
    :tooltipHelp="tooltipHelp"
  />

  <Fieldset
    :id="idPrefix"
    :legend="startCase(resolvedSchema?.title || keyName)"
    :collapsed="collapsed"
    toggleable
    v-else-if="isAnyOf && selectedSchema && !isNull(selectedOption)"
  >
    <SelectField
      v-if="anyOfOptions?.length > 1"
      :label="resolvedSchema.title || keyName"
      :options="anyOfOptions"
      v-model="selectedOption"
      :tooltipHelp="tooltipHelp"
    />
    <RecursiveField
      :collapsed="anyOfOptions?.length === 0"
      :idPrefix="`${idPrefix}-${[selectedOption, ...path].join('-')}`"
      :key="selectedOption"
      :schema="selectedSchema"
      :model="model"
      :path="path"
      :defs="defs"
    />
  </Fieldset>
  <div v-else-if="isAnyOf">
    <SelectField
      v-if="anyOfOptions?.length > 1"
      :label="resolvedSchema.title || keyName"
      :options="anyOfOptions"
      v-model="selectedOption"
      :tooltipHelp="tooltipHelp"
    />
    <div v-if="selectedSchema && !isNull(selectedOption)">
      <RecursiveField
        :collapsed="anyOfOptions?.length === 0"
        :idPrefix="`${idPrefix}-${[selectedOption, ...path].join('-')}`"
        :key="[selectedOption, ...path].join('-')"
        :schema="selectedSchema"
        :model="model"
        :path="path"
        :defs="defs"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import type { Component } from "vue";
import TextField from "@/ui/TextField.vue";
import NumberInputField from "@/ui/NumberInputField.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import SelectField from "@/ui/SelectField.vue";
import type { InputNumberProps } from "primevue/inputnumber";
import { renameKeys } from "rename-obj-map";
import { startCase, trimSuffix } from "@/util/str";
import type {
  JSONSchema,
  FieldType,
  TypeOption,
} from "@/features/controller/interface";
import HexField from "@/ui/HexField.vue";
import {
  isString,
  isPlainObject,
  isNull,
  isNil,
  isUndefined,
  isEmptyArray,
} from "@/util/guards";
import StringOrNumberField from "@/ui/StringOrNumberField.vue";
import RecursiveField from "./RecursiveField.vue";
import { pick } from "@/util/obj";
import Fieldset from "@/ui/Fieldset.vue";

const props = withDefaults(
  defineProps<{
    schema: JSONSchema | null;
    model: Record<string | number, any> | null;
    path: (string | number)[];
    keyName?: string;
    defs?: Record<string, JSONSchema>;
    idPrefix: string;
    removable?: boolean;
    tooltipHelp?: string;
    collapsed?: boolean;
  }>(),
  {
    collapsed: true,
  },
);

const components: Partial<Record<FieldType, [Component, object]>> = {
  integer: [NumberInputField, { step: 1 }],
  string: [TextField, { fieldClassName: "w-full" }],
  string_or_number: [
    StringOrNumberField,
    { min: 1, inputClassName: "!w-full" },
  ],
  number: [
    NumberInputField,
    {
      step: 0.1,
      minFractionDigits: 1,
    } as InputNumberProps,
  ],
  boolean: [ToggleSwitchField, {}],
  hex: [HexField, { min: 1, inputClassName: "!w-full" }],
};

const comp = computed(() => {
  if (!resolvedSchema.value?.type) {
    return;
  }
  const pair = components[resolvedSchema.value?.type];
  if (!pair) {
    return;
  }
  return pair[0];
});
const compProps = computed(() => {
  const resSchema = resolvedSchema.value;
  if (!resSchema?.type) {
    return;
  }
  const pair = components[resSchema.type];

  if (!pair) {
    return;
  }

  const props = pair[1];
  const extraProps = renameKeys(
    { maximum: "max", minimum: "min", const: "readonly" },
    pick(
      ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "const"],
      resSchema,
    ),
  );

  return {
    ...props,
    ...extraProps,
    readonly: !!extraProps.readonly,
    ...resSchema.props,
  };
});

function fillDefaults(target: any, schema: JSONSchema): void {
  if (!schema || !target) return;
  if (schema.type === "object" && schema.properties) {
    for (const [key, propSchema] of Object.entries(schema.properties)) {
      if (
        isUndefined(target[key]) &&
        !isUndefined((propSchema as any).default)
      ) {
        target[key] = (propSchema as any).default;
      }
      if (
        propSchema &&
        typeof target[key] === "object" &&
        propSchema.type === "object"
      ) {
        fillDefaults(target[key], propSchema);
      }
    }
  }
}

function resolveRef(schema: JSONSchema | TypeOption) {
  if (schema?.$ref && props.defs) {
    const refMatch = schema.$ref.match(/^#\/\$defs\/(.+)$/);
    if (refMatch) {
      const defKey = refMatch[1];
      return props.defs[defKey] || schema;
    }
  }
}
const getNestedValue = <Obj extends Record<string | number, any> | null>(
  obj: Obj,
  keys: (string | number)[],
) => keys.reduce((acc, key) => (acc ? acc[key] : undefined), obj);

const setNestedValue = <Obj extends Record<string, any> | null>(
  obj: Obj,
  keys: (string | number)[],
  value: any,
): void => {
  if (!obj) {
    return;
  }
  keys.reduce((acc, key, index) => {
    if (index === keys.length - 1) {
      acc[key] = value;
    } else {
      if (isNil(acc[key])) {
        acc[key] = {};
      }
      return acc[key];
    }
  }, obj);
};

const resolvedSchema = computed(() =>
  props.schema ? resolveRef(props.schema) || props.schema : props.schema,
);

const tooltipHelp = computed(() => {
  if (props.tooltipHelp) {
    return props.tooltipHelp;
  }
  if (!resolvedSchema.value) {
    return;
  }
  const examples = resolvedSchema.value.examples?.map((it) => `${it}`);
  const examplesStr = examples && examples.length > 0 && examples.join(", ");
  const description =
    resolvedSchema.value.description || resolvedSchema.value.tooltipHelp;
  if (description) {
    return [trimSuffix(description, ".").trim(), examplesStr]
      .filter(Boolean)
      .join(", e.g. ");
  }

  return examplesStr ? `Examples: ${examplesStr}` : undefined;
});

const localValue = computed({
  get() {
    return getNestedValue(props.model, props.path);
  },
  set(val) {
    setNestedValue(props.model, props.path, val);
  },
});

const isObjectSchema = computed(
  () =>
    resolvedSchema.value?.type === "object" &&
    !!resolvedSchema.value.properties,
);

const isArraySchema = computed(
  () => resolvedSchema.value?.type === "array" && resolvedSchema.value.items,
);

const isAnyOf = computed(
  () =>
    !!(
      resolvedSchema.value?.anyOf && Array.isArray(resolvedSchema.value?.anyOf)
    ) ||
    !!(
      resolvedSchema.value?.oneOf && Array.isArray(resolvedSchema.value?.oneOf)
    ),
);

const enumOptions = computed(
  () =>
    Array.isArray(resolvedSchema.value?.enum) &&
    resolvedSchema.value?.enum.map((value) => ({
      value,
      label: isString(value) ? startCase(value) : `${value}`,
    })),
);

const effectiveAnyOf = computed(() => {
  const schemas =
    resolvedSchema.value?.items?.anyOf ||
    resolvedSchema.value?.items?.oneOf ||
    resolvedSchema.value?.anyOf ||
    resolvedSchema.value?.oneOf;

  return (schemas || []).map((opt) => resolveRef(opt) || opt);
});

const detectedCandidateIndex = computed(() => {
  if (!localValue.value || isEmptyArray(effectiveAnyOf.value)) {
    return 0;
  }
  const data = localValue.value;
  let bestIndex = 0;
  let bestScore = -1;

  effectiveAnyOf.value.forEach((schema, index) => {
    let score = 0;
    if (schema.properties) {
      Object.keys(schema.properties).forEach((prop) => {
        if (data.hasOwnProperty(prop)) {
          score++;
        }
      });
    }
    if (score > bestScore) {
      bestScore = score;
      bestIndex = index;
    }
  });
  return bestIndex;
});

const selectedOption = computed({
  get() {
    if (
      !isNull(localValue.value) &&
      isPlainObject(localValue.value) &&
      !isUndefined(localValue.value._optionSelected)
    ) {
      return localValue.value._optionSelected;
    }

    return detectedCandidateIndex.value;
  },
  set(val) {
    if (isNull(val)) {
      localValue.value = null;
    } else {
      if (isNull(localValue.value) || !isPlainObject(localValue.value)) {
        localValue.value = {};
      }
      localValue.value._optionSelected = val;
    }
  },
});

const anyOfOptions = computed(() => {
  if (!effectiveAnyOf.value.length) return [];

  const options = effectiveAnyOf.value.map((sch, i) => {
    let label = "";
    if (sch.title) {
      label = sch.title;
    } else if (sch.$ref) {
      label = sch.$ref.split("/").pop() || `Option ${i + 1}`;
    } else if (sch.type) {
      label = sch.type;
    } else {
      label = `Option ${i + 1}`;
    }
    return { value: i, label: startCase(label) };
  });

  return options;
});
const selectedSchema = computed(() => {
  const options = effectiveAnyOf.value;
  if (!options || isEmptyArray(options)) {
    return null;
  }
  if (options.length === 1) {
    return options[0];
  }

  const index = selectedOption.value ?? 0;
  return resolveRef(options[index]) || options[index];
});

const keyName = computed(() => props.keyName || "");

const handleRemoveArrayItem = (indexToRemove: number) => {
  const parentArray = getNestedValue(props.model, props.path);
  if (Array.isArray(parentArray)) {
    parentArray.splice(Number(indexToRemove), 1);
  }
};

const handleAddListItem = () => {
  if (!Array.isArray(localValue.value)) {
    localValue.value = [];
  }

  let option = 0;

  let newItem: any;
  if (resolvedSchema.value?.items && resolvedSchema.value.items.anyOf) {
    newItem = { _optionSelected: option };
    const selectedSchema =
      (resolvedSchema.value.items.anyOf[option] &&
        resolveRef(resolvedSchema.value.items.anyOf[option])) ||
      ({} as JSONSchema);
    if (selectedSchema.type === "object") {
      fillDefaults(newItem, selectedSchema);
    }
  } else if (
    resolvedSchema.value?.items &&
    resolvedSchema.value.items.type === "object"
  ) {
    newItem = {};
    fillDefaults(newItem, resolvedSchema.value.items);
  } else if (resolvedSchema.value?.items && resolvedSchema.value.items.enum) {
    newItem = resolvedSchema.value.items.enum[0];
  } else {
    newItem = null;
  }
  localValue.value.push(newItem);
};

watch(
  localValue,
  (newVal) => {
    if (isNil(newVal)) {
      if (resolvedSchema.value?.type === "object") {
        setNestedValue(props.model, props.path, { _optionSelected: newVal });
      }
    }
  },
  { immediate: true },
);
watch(
  localValue,
  (newVal) => {
    if (Array.isArray(newVal)) {
      newVal.forEach((item) => {
        if (item && isPlainObject(item) && isUndefined(item._optionSelected)) {
          item._optionSelected = detectedCandidateIndex.value || 0;
        }
      });
    }
  },
  { immediate: true, deep: true },
);

watch(selectedOption, (newOpt, oldOpt) => {
  if (newOpt !== oldOpt) {
    setNestedValue(props.model, props.path, { _optionSelected: newOpt });
    const branchModel = getNestedValue(props.model, props.path);
    if (selectedSchema.value && isPlainObject(branchModel)) {
      fillDefaults(branchModel, selectedSchema.value);
    }
  }
});
</script>
