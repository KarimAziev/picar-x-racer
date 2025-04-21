<template>
  <div v-if="isObjectSchema && resolvedSchema">
    <Fieldset
      :legend="startCase(resolvedSchema.title || keyName)"
      toggleable
      collapsed
    >
      <div
        v-for="(propSchema, propName) in resolvedSchema.properties"
        :key="propName"
      >
        <RecursiveField
          :key="[selectedOption, ...path].join('-')"
          :schema="propSchema"
          :model="model"
          :path="[...path, propName]"
          :defs="defs"
        />
      </div>
    </Fieldset>
  </div>

  <div v-else-if="isArraySchema && resolvedSchema && arraySchemaOptions">
    <Fieldset
      :legend="startCase(resolvedSchema.title || keyName)"
      toggleable
      collapsed
    >
      <div v-for="(propSchema, propName) in arraySchemaOptions" :key="propName">
        <RecursiveField
          :key="[selectedOption, ...path].join('-')"
          :schema="propSchema"
          :model="model"
          :path="[...path, propName]"
          :defs="defs"
          :tooltipHelp="resolvedSchema?.description"
        />
      </div>
    </Fieldset>
  </div>

  <div v-else-if="enumOptions">
    <SelectField
      :label="resolvedSchema.title || keyName"
      :options="enumOptions"
      v-model="localValue"
      :tooltipHelp="resolvedSchema?.description"
    />
  </div>

  <div v-else-if="resolvedSchema?.type && components[resolvedSchema?.type]">
    <component
      :is="components[resolvedSchema?.type]"
      v-model="localValue"
      :label="resolvedSchema.title || keyName"
      :tooltipHelp="resolvedSchema.description"
    />
  </div>

  <Fieldset
    :legend="startCase(resolvedSchema?.title || keyName)"
    toggleable
    collapsed
    v-else-if="isAnyOf && selectedOption !== null && selectedSchema"
  >
    <SelectField
      v-if="anyOfOptions?.length > 1"
      :label="resolvedSchema.title || keyName"
      :options="anyOfOptions"
      v-model="selectedOption"
      :tooltipHelp="resolvedSchema?.description"
    />
    <RecursiveField
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
      :tooltipHelp="resolvedSchema?.description"
    />
    <div v-if="selectedOption !== null && selectedSchema">
      <RecursiveField
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
import Fieldset from "primevue/fieldset";
import RecursiveField from "./RecursiveField.vue";
import { startCase } from "@/util/str";
import type {
  JSONSchema,
  FieldType,
  TypeOption,
} from "@/features/controller/interface";
import HexField from "@/ui/HexField.vue";
import { isString } from "@/util/guards";
import StringOrNumberField from "@/ui/StringOrNumberField.vue";

const props = defineProps<{
  schema: JSONSchema | null;
  model: Record<string, any>;

  path: (string | number)[];
  keyName?: string;

  defs?: Record<string, JSONSchema>;
}>();

const components: Partial<Record<FieldType, Component>> = {
  integer: NumberInputField,
  string: TextField,
  string_or_number: StringOrNumberField,
  number: NumberInputField,
  boolean: ToggleSwitchField,
  hex: HexField,
};

function resolveRef(schema: JSONSchema | TypeOption) {
  if (schema?.$ref && props.defs) {
    const refMatch = schema.$ref.match(/^#\/\$defs\/(.+)$/);
    if (refMatch) {
      const defKey = refMatch[1];
      return props.defs[defKey] || schema;
    }
  }
}

const resolvedSchema = computed(() => {
  return props.schema ? resolveRef(props.schema) || props.schema : props.schema;
});

function getNestedValue(obj: any, keys: (string | number)[]): any {
  const data = keys.reduce((acc, key) => (acc ? acc[key] : undefined), obj);
  return data;
}
function setNestedValue(obj: any, keys: (string | number)[], value: any): void {
  keys.reduce((acc, key, index) => {
    if (index === keys.length - 1) {
      acc[key] = value;
    } else {
      if (acc[key] === undefined || acc[key] === null) {
        acc[key] = {};
      }
      return acc[key];
    }
  }, obj);
}

const localValue = computed({
  get() {
    const value = getNestedValue(props.model, props.path);

    return value;
  },
  set(val) {
    setNestedValue(props.model, props.path, val);
  },
});

const isObjectSchema = computed(() => {
  return (
    resolvedSchema.value?.type === "object" && !!resolvedSchema.value.properties
  );
});

const isArraySchema = computed(() => {
  return resolvedSchema.value?.type === "array" && resolvedSchema.value.items;
});

const isAnyOf = computed(() => {
  return (
    !!(
      resolvedSchema.value?.anyOf && Array.isArray(resolvedSchema.value?.anyOf)
    ) ||
    !!(
      resolvedSchema.value?.oneOf && Array.isArray(resolvedSchema.value?.oneOf)
    )
  );
});

const arraySchemaOptions = computed(() => {
  if (!isArraySchema.value || !resolvedSchema.value?.items) {
    return;
  }
  const items = resolvedSchema.value?.items;

  if (Array.isArray(items.anyOf) || Array.isArray(items.oneOf)) {
    return (items?.anyOf || items?.oneOf)?.map(
      (item) => resolveRef(item) || item,
    );
  }

  if (items.$ref) {
    return resolveRef(items);
  }
});

const enumOptions = computed(() => {
  const options =
    Array.isArray(resolvedSchema.value?.enum) &&
    resolvedSchema.value?.enum.map((value) => ({
      value,
      label: isString(value) ? startCase(value) : `${value}`,
    }));

  return options;
});

const effectiveAnyOf = computed(() => {
  const options =
    resolvedSchema.value?.anyOf || resolvedSchema.value?.oneOf || [];
  if (!Array.isArray(options)) return [];
  const resolvedOptions = options.map((opt) => resolveRef(opt) || opt);
  const nonNullOptions = resolvedOptions.filter((opt) =>
    opt.type ? opt.type !== "null" : true,
  );
  return nonNullOptions.length === 1 ? nonNullOptions : resolvedOptions;
});

const detectedCandidateIndex = computed(() => {
  const data = localValue.value;
  const candidates = effectiveAnyOf.value;
  if (!data || !candidates.length) return 0;
  let bestIndex = 0;
  let bestScore = -1;
  candidates.forEach((schema, index) => {
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
      localValue.value !== null &&
      typeof localValue.value === "object" &&
      localValue.value._optionSelected !== undefined
    ) {
      return localValue.value._optionSelected;
    }

    return detectedCandidateIndex.value;
  },
  set(val) {
    if (val === null) {
      localValue.value = null;
    } else {
      if (typeof localValue.value !== "object" || localValue.value === null) {
        localValue.value = {};
      }
      localValue.value._optionSelected = val;
    }
  },
});

const anyOfOptions = computed(() => {
  if (!isAnyOf.value) return [];
  return effectiveAnyOf.value.map((sch, i) => {
    const label =
      sch.title ||
      (sch.$ref ? sch.$ref.split("/").pop() : null) ||
      sch.type ||
      `Option ${i + 1}`;
    const finalLabel = startCase(label);
    return {
      label: finalLabel === "Null" ? "None" : finalLabel,
      value: finalLabel === "Null" ? null : i,
    };
  });
});
const selectedSchema = computed(() => {
  let options = effectiveAnyOf.value;
  if (!options || options.length === 0) return null;
  if (options.length === 1) {
    return options[0];
  }

  const index = selectedOption.value ?? 0;
  return resolveRef(options[index]) || options[index];
});

const keyName = computed(() => props.keyName || "");

watch(
  localValue,
  (newVal) => {
    if (newVal === undefined || newVal === null) {
      if (resolvedSchema.value?.type === "object") {
        setNestedValue(props.model, props.path, { _optionSelected: newVal });
      }
    }
  },
  { immediate: true },
);

watch(selectedOption, (newOpt, oldOpt) => {
  if (newOpt !== oldOpt) {
    setNestedValue(props.model, props.path, { _optionSelected: newOpt });
  }
});
</script>
