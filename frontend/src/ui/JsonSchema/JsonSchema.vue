<template>
  <template v-if="isObjectSchema && resolvedSchema">
    <Fieldset
      v-if="level < 2"
      :legend="startCase(resolvedSchema.title)"
      toggleable
      :collapsed="collapsed"
      :id="idPrefix"
    >
      <ExpandableText
        v-if="resolvedSchema.description"
        :class="{
          'truncated-label': level >= 2,
          'max-w-[280px] min-[400px]:max-w-[380px] md:max-w-[420px] lg:max-w-[440px] xl:max-w-[540px] 2xl:max-w-[490px]':
            level < 2,
        }"
        :text="resolvedSchema.description"
        lineClampClass="line-clamp-1"
      ></ExpandableText>
      <Divider v-if="resolvedSchema.description" />

      <div
        :class="{
          'grid grid-cols-2 gap-2 justify-around': level < 2,
        }"
      >
        <JsonSchema
          :origModel="origModel"
          v-for="(propSchema, propName) in resolvedSchema.properties"
          :level="level + 1"
          :idPrefix="`${idPrefix}-${[selectedOption, ...path].join('-')}`"
          :key="[selectedOption, ...path, propName].join('-')"
          :schema="propSchema"
          :model="model"
          :path="[...path, propName]"
          :defs="defs"
        />
      </div>
      <div v-if="level === 0" class="mt-2">
        <Button
          outlined
          :disabled="disabled"
          @click="handleSave"
          label="Save"
          size="small"
        />
      </div>
    </Fieldset>
    <div v-else>
      <h4 class="font-bold">
        {{ startCase(resolvedSchema.title) }}
      </h4>
      <ExpandableText
        v-if="resolvedSchema.description"
        :class="{
          'truncated-label': level >= 2,
          'max-w-[280px] min-[400px]:max-w-[380px] md:max-w-[420px] lg:max-w-[440px] xl:max-w-[540px] 2xl:max-w-[490px]':
            level < 2,
        }"
        :text="resolvedSchema.description"
        lineClampClass="line-clamp-1"
      ></ExpandableText>
      <Divider v-if="resolvedSchema.description && level < 2" />

      <JsonSchema
        :origModel="origModel"
        v-for="(propSchema, propName) in resolvedSchema.properties"
        :level="level + 1"
        :key="[selectedOption, ...path, propName].join('-')"
        :idPrefix="`${idPrefix}-${[selectedOption, ...path].join('-')}`"
        :schema="propSchema"
        :model="model"
        :path="[...path, propName]"
        :defs="defs"
      />
    </div>
  </template>

  <div v-else-if="isArraySchema && resolvedSchema">
    <Fieldset
      :legend="startCase(resolvedSchema.title)"
      toggleable
      :id="idPrefix"
      :collapsed="collapsed"
    >
      <div v-for="(_, index) in localValue" :key="index" class="mb-4">
        <div class="grid grid-cols-[80%_20%] gap-2">
          <SelectField
            :label="resolvedSchema.title"
            :options="anyOfOptions"
            v-model="selections[index as number]"
            :tooltipHelp="tooltipHelp"
          />
          <Button
            @click="handleRemoveArrayItem(index as number)"
            icon="pi pi-times"
            class="p-button-rounded p-button-danger p-button-text"
          />
        </div>
        <JsonSchema
          :origModel="origModel"
          :level="level + 1"
          :collapsed="false"
          :idPrefix="`${idPrefix}-${[selections[index as number], ...path, index].join('-')}`"
          :key="[selections[index as number], ...path, index].join('-')"
          :schema="
            (resolvedSchema.items?.anyOf
              ? resolveRef(
                  resolvedSchema.items?.anyOf[selections[index as number]],
                  defs,
                )
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
  <template v-else-if="compWithProps">
    <component
      v-if="!compWithProps.props.hidden"
      :is="compWithProps.comp"
      v-bind="compWithProps.props"
      v-model="localValue"
      :field="`${stringifyArrSafe(path)}`"
      :label="resolvedSchema?.title"
      :path="path"
      :tooltipHelp="tooltipHelp"
    />
  </template>
  <SelectField
    :field="`${stringifyArrSafe(path)}`"
    v-else-if="enumOptions"
    :label="resolvedSchema?.title ? startCase(resolvedSchema?.title) : null"
    :options="enumOptions"
    v-model="localValue"
    :tooltipHelp="tooltipHelp"
  />

  <Fieldset
    :id="idPrefix"
    :legend="
      resolvedSchema?.title ? startCase(resolvedSchema?.title) : undefined
    "
    :collapsed="collapsed"
    toggleable
    v-else-if="isAnyOf && selectedSchema && !isNull(selectedOption)"
  >
    <SelectField
      :field="`select-${stringifyArrSafe(path)}`"
      v-if="anyOfOptions?.length > 1"
      :label="resolvedSchema?.title"
      :options="anyOfOptions"
      v-model="selectedOption"
      :tooltipHelp="tooltipHelp"
      @update:model-value="handleNewOption"
    />
    <JsonSchema
      :level="level + 1"
      :origModel="origModel"
      :collapsed="anyOfOptions?.length === 0"
      :idPrefix="`${idPrefix}-${[selectedOption, ...path].join('-')}`"
      :key="`schema-${stringifyArrSafe([...path, selectedOption])}`"
      :schema="selectedSchema"
      :model="model"
      :path="path"
      :defs="defs"
    />
    <div v-if="level === 0" class="mt-2">
      <Button
        outlined
        :disabled="disabled"
        @click="handleSave"
        label="Save"
        size="small"
      />
    </div>
  </Fieldset>
  <div v-else-if="isAnyOf">
    <SelectField
      v-if="anyOfOptions?.length > 1"
      :field="`${stringifyArrSafe([...path, selectedOption])}`"
      :label="`Any of ${resolvedSchema?.title}`"
      :options="anyOfOptions"
      v-model="selectedOption"
      :tooltipHelp="tooltipHelp"
    />
    <div v-if="selectedSchema && !isNull(selectedOption)">
      <JsonSchema
        :level="level + 1"
        :origModel="origModel"
        :collapsed="anyOfOptions?.length === 0"
        :idPrefix="`${idPrefix}-${[selectedOption, ...path].join('-')}`"
        :key="`${stringifyArrSafe([...path, selectedOption])}`"
        :schema="selectedSchema"
        :model="model"
        :path="path"
        :defs="defs"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, ref } from "vue";
import type { JSONSchema } from "@/ui/JsonSchema/interface";
import { isPlainObject, isNull } from "@/util/guards";
import { cloneDeep, isObjectEquals } from "@/util/obj";
import { startCase, stringifyArrSafe } from "@/util/str";
import Fieldset from "@/ui/Fieldset.vue";
import SelectField from "@/ui/SelectField.vue";
import ExpandableText from "@/ui/ExpandableText.vue";
import {
  setNestedValue,
  getNestedValue,
  mapAnyOfOptions,
  detectCandidateIndex,
  fillDefaults,
  resolveRef,
  mapEffectiveAnyOf,
  isObjectSchemaPred,
  isArraySchemaPred,
  isAnyOfPred,
  getTooltipHelp,
  getSelectedSchema,
  mapEnumOptions,
  getComponentWithProps,
} from "@/ui/JsonSchema/util";
import JsonSchema from "./JsonSchema.vue";

const props = withDefaults(
  defineProps<{
    schema: JSONSchema | null;
    model: Record<string | number, any> | null;
    origModel: Record<string | number, any> | null;
    path: (string | number)[];
    defs?: Record<string, JSONSchema>;
    idPrefix: string;
    tooltipHelp?: string;
    collapsed?: boolean;
    level: number;
    dataComparator?: <
      V extends Record<string, any>,
      B extends Record<string, any>,
    >(
      origData: V,
      newData: B,
    ) => boolean;
  }>(),
  {
    level: 0,
    collapsed: true,
    dataComparator: <
      V extends Record<string, any>,
      B extends Record<string, any>,
    >(
      origData: V,
      newData: B,
    ) => isObjectEquals(origData, newData),
  },
);

const emit = defineEmits(["handleSave"]);

const resolvedSchema = computed(() =>
  props.schema
    ? resolveRef(props.schema, props.defs) || props.schema
    : props.schema,
);

const compWithProps = computed(() =>
  getComponentWithProps(resolvedSchema.value),
);

const tooltipHelp = computed(
  () => props.tooltipHelp || getTooltipHelp(resolvedSchema.value),
);

const localValue = computed({
  get() {
    return getNestedValue(props.model, props.path);
  },
  set(val) {
    setNestedValue(props.model, props.path, val);
  },
});

const isObjectSchema = computed(() => isObjectSchemaPred(resolvedSchema.value));
const isArraySchema = computed(() => isArraySchemaPred(resolvedSchema.value));
const isAnyOf = computed(() => isAnyOfPred(resolvedSchema.value));
const enumOptions = computed(() => mapEnumOptions(resolvedSchema.value));
const effectiveAnyOf = computed(() =>
  mapEffectiveAnyOf(resolvedSchema.value, props.defs),
);
const anyOfOptions = computed(() => mapAnyOfOptions(effectiveAnyOf.value));
const detectedCandidateIndex = computed(() =>
  detectCandidateIndex(localValue.value, effectiveAnyOf.value),
);

const selections = ref<number[]>([]);
const oldData = ref<Record<string, any>>({});

const optionSelectedRef = ref(detectedCandidateIndex.value);
const prevSelectedOpt = ref(detectedCandidateIndex.value);

const selectedOption = computed({
  get() {
    return optionSelectedRef.value;
  },
  set(val) {
    optionSelectedRef.value = val;
  },
});

const selectedSchema = computed(() =>
  getSelectedSchema(effectiveAnyOf.value, selectedOption.value, props.defs),
);

const disabled = computed(() => {
  if (props.level !== 0) {
    return true;
  }
  const storedData = getNestedValue(props.origModel, props.path);
  const diff =
    isPlainObject(storedData) && isPlainObject(localValue.value)
      ? props.dataComparator(storedData, localValue.value)
      : false;
  return !diff;
});

const handleSave = () => {
  if (props.model) {
    const key = props.path[0];
    emit("handleSave", { [key]: props.model[key] });
  }
};

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

  let newItem: any;

  if (resolvedSchema.value?.items && resolvedSchema.value.items.anyOf) {
    newItem = {};

    const selectedBranch =
      resolvedSchema.value.items.anyOf[optionSelectedRef.value] &&
      resolveRef(
        resolvedSchema.value.items.anyOf[optionSelectedRef.value],
        props.defs,
      );

    if (selectedBranch && selectedBranch.type === "object") {
      fillDefaults(newItem, selectedBranch);
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

const handleNewOption = () => {
  const oldOpt = prevSelectedOpt.value;
  const newOpt = selectedOption.value;
  const prevData = oldData.value[newOpt];

  oldData.value[oldOpt] = cloneDeep(getNestedValue(props.model, props.path));

  const branchModel = getNestedValue(props.model, props.path);

  if (prevData) {
    localValue.value = prevData;
  } else {
    if (selectedSchema.value && isPlainObject(branchModel)) {
      fillDefaults(branchModel, selectedSchema.value);
    }
  }

  prevSelectedOpt.value = newOpt;
};

watch(
  localValue,
  (newItems) => {
    if (Array.isArray(newItems)) {
      selections.value = newItems.map((_) => detectedCandidateIndex.value || 0);
    }
  },
  { immediate: true },
);

watch(detectedCandidateIndex, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    optionSelectedRef.value = newVal;
  }
});

defineExpose({
  localValue,
  selectedOption,
  oldData,
  handleNewOption,
});
</script>
