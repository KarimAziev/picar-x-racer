<template>
  <FieldsPanel
    v-if="isObjectSchema && resolvedSchema"
    :level="level"
    :inhibitFieldset="inhibitFieldset"
    :title="resolvedSchema.title"
    :collapsed="collapsed"
    :idPrefix="idPrefix"
    :description="resolvedSchema.description"
  >
    <Grid :inhibit-grid="level > 1">
      <JsonSchema
        :origModel="origModel"
        v-for="(propSchema, propName) in resolvedSchema.properties"
        :level="level + 1"
        :idPrefix="`${idPrefix}-${[selectedOption, ...path].join('-')}`"
        :key="[selectedOption, ...path, propName].join('-')"
        :schema="propSchema"
        :model="model"
        :invalidData="invalidData"
        :path="[...path, propName]"
        :defs="defs"
      />
      <slot></slot>
    </Grid>
    <Footer v-if="isRootLevel">
      <Button
        outlined
        :disabled="disabled"
        @click="handleSave"
        label="Save"
        size="small"
      />
    </Footer>
  </FieldsPanel>

  <FieldsPanel
    v-else-if="isArraySchema && resolvedSchema"
    :level="level"
    :inhibitFieldset="inhibitFieldset"
    :title="resolvedSchema.title"
    :collapsed="collapsed"
    :idPrefix="idPrefix"
    :description="resolvedSchema.description"
  >
    <div v-for="(_, index) in localValue" :key="index" class="mb-4">
      <ArraySelectWrapper v-if="anyOfOptions && !!anyOfOptions.length">
        <SelectField
          :label="resolvedSchema.title"
          :options="anyOfOptions"
          v-model="selections[index as number]"
          :tooltipHelp="tooltipHelp"
        />
      </ArraySelectWrapper>
      <ArrayPanel @remove:click="handleRemoveArrayItem(index as number)">
        <JsonSchema
          inhibitFieldset
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
          :invalidData="invalidData"
          :path="[...path, index]"
          :defs="defs"
        ></JsonSchema>
      </ArrayPanel>
      <slot></slot>
    </div>
    <Footer>
      <Button
        size="small"
        icon="pi pi-plus"
        label="Add Item"
        @click="handleAddListItem"
        class="w-fit"
        severity="secondary"
      />
      <Button
        v-if="isRootLevel"
        outlined
        :disabled="disabled"
        @click="handleSave"
        label="Save"
        size="small"
      />
    </Footer>
  </FieldsPanel>

  <template v-else-if="compWithProps">
    <component
      v-if="!compWithProps.props.hidden"
      :is="compWithProps.comp"
      v-bind="compWithProps.props"
      v-model="localValue"
      messageClass="min-h-[17px] absolute bottom-0 left-1.5"
      :field="`${stringifyArrSafe(path)}`"
      :label="resolvedSchema?.title"
      :path="path"
      :tooltipHelp="tooltipHelp"
      :invalid="!!invalidMessage"
      :message="isString(invalidMessage) ? invalidMessage : null"
    />
    <slot></slot>
  </template>

  <template v-else-if="enumOptions">
    <SelectField
      :field="`${stringifyArrSafe(path)}`"
      :label="resolvedSchema?.title ? startCase(resolvedSchema?.title) : null"
      :options="enumOptions"
      v-model="localValue"
      :tooltipHelp="tooltipHelp"
    />
    <slot></slot>
  </template>

  <FieldsPanel
    v-else-if="isAnyOf"
    :level="level"
    :inhibitFieldset="inhibitFieldset"
    :idPrefix="idPrefix"
    :title="resolvedSchema?.title"
    :collapsed="collapsed"
    toggleable
  >
    <SelectField
      v-if="anyOfOptions?.length > 1"
      :field="`select-${stringifyArrSafe(path)}`"
      class="mb-2"
      :label="resolvedSchema?.title"
      :options="anyOfOptions"
      v-model="selectedOption"
      :tooltipHelp="tooltipHelp"
      @update:model-value="handleNewOption"
    />

    <JsonSchema
      v-if="selectedSchema"
      :inhibitFieldset="anyOfOptions?.length > 1"
      :level="level + 1"
      :origModel="origModel"
      :collapsed="anyOfOptions?.length === 0"
      :idPrefix="`${idPrefix}-${[selectedOption, ...path].join('-')}`"
      :key="`schema-${stringifyArrSafe([...path, selectedOption])}`"
      :schema="selectedSchema"
      :model="model"
      :invalidData="invalidData"
      :path="path"
      :defs="defs"
    />
    <slot></slot>
    <Footer v-if="isRootLevel">
      <Button
        outlined
        :disabled="disabled"
        @click="handleSave"
        label="Save"
        size="small"
      />
    </Footer>
  </FieldsPanel>
</template>

<script setup lang="ts">
import { computed, watch, ref } from "vue";
import type { JSONSchema } from "@/ui/JsonSchema/interface";
import { isPlainObject, isString } from "@/util/guards";
import { cloneDeep, isObjectEquals } from "@/util/obj";
import { startCase, stringifyArrSafe } from "@/util/str";
import SelectField from "@/ui/SelectField.vue";
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
  resolveNewListItem,
} from "@/ui/JsonSchema/util";
import JsonSchema from "./JsonSchema.vue";
import Footer from "@/ui/JsonSchema/Footer.vue";
import Grid from "@/ui/JsonSchema/Grid.vue";
import ArrayPanel from "@/ui/JsonSchema/ArrayPanel.vue";
import ArraySelectWrapper from "@/ui/JsonSchema/ArraySelectWrapper.vue";
import FieldsPanel from "@/ui/JsonSchema/FieldsPanel.vue";

const props = withDefaults(
  defineProps<{
    schema: JSONSchema | null;
    model: Record<string | number, any> | null;
    origModel: Record<string | number, any> | null;
    invalidData?: Record<string | number, any> | null;
    path: (string | number)[];
    defs?: Record<string, JSONSchema>;
    idPrefix: string;
    tooltipHelp?: string;
    collapsed?: boolean;
    level: number;
    inhibitFieldset?: boolean;
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

const emit = defineEmits<{
  (e: "handleSave", data: Record<string, any>): void;
  (e: "remove", data: Record<string, any>): void;
}>();

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

const invalidMessage = computed(() =>
  props.invalidData ? getNestedValue(props.invalidData, props.path) : false,
);

const isObjectSchema = computed(() => isObjectSchemaPred(resolvedSchema.value));
const isArraySchema = computed(() => isArraySchemaPred(resolvedSchema.value));
const isAnyOf = computed(() => isAnyOfPred(resolvedSchema.value));
const enumOptions = computed(() => mapEnumOptions(resolvedSchema.value));
const effectiveAnyOf = computed(() =>
  mapEffectiveAnyOf(resolvedSchema.value, props.defs),
);
const anyOfOptions = computed(() => mapAnyOfOptions(effectiveAnyOf.value));
const detectedCandidateIndex = computed(() =>
  detectCandidateIndex(
    localValue.value,
    effectiveAnyOf.value,
    resolvedSchema.value,
    props.defs,
  ),
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

const isRootLevel = computed(() => props.level === 0);

const disabled = computed(() => {
  if (!isRootLevel.value) {
    return true;
  }

  const invalid = invalidMessage.value;

  if (invalid) {
    return true;
  }

  const storedData = getNestedValue(props.origModel, props.path);
  if (Array.isArray(localValue.value)) {
    if (
      !Array.isArray(storedData) ||
      storedData.length !== localValue.value!.length
    ) {
      return false;
    }
    return !storedData.some((a, i) =>
      isPlainObject(a) && isPlainObject(localValue.value![i])
        ? props.dataComparator(a, localValue.value![i])
        : isPlainObject(a) || isPlainObject(localValue.value![i]),
    );
  }
  const diff =
    isPlainObject(storedData) && isPlainObject(localValue.value)
      ? props.dataComparator(storedData, localValue.value)
      : isPlainObject(storedData) || isPlainObject(localValue.value);
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
  const newItem = resolveNewListItem(
    resolvedSchema.value,
    optionSelectedRef.value,
    props.defs,
  );

  localValue.value.push(newItem);
};

const handleNewOption = () => {
  const oldOpt = prevSelectedOpt.value;
  const newOpt = selectedOption.value;
  const prevData = oldData.value[newOpt];
  const branchModel = getNestedValue(props.model, props.path);
  oldData.value[oldOpt] = cloneDeep(branchModel);

  if (prevData) {
    localValue.value = prevData;
  } else if (selectedSchema.value && isPlainObject(branchModel)) {
    fillDefaults(branchModel, selectedSchema.value);
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
