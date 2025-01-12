import { onMounted, watch, reactive } from "vue";
import type { DetectionSettings } from "@/features/detection/store";
import { useStore as useDetectionStore } from "@/features/detection/store";
import { useAsyncDebounce } from "@/composables/useDebounce";
import { roundNumber } from "@/util/number";
import { isNumber } from "@/util/guards";
import { evolve, isObjectEquals } from "@/util/obj";

const normalizeValue = (val: string | null): Record<string, boolean> => {
  return val ? { [val]: true } : {};
};

const denormalizeValue = (val: ReturnType<typeof normalizeValue>) =>
  Object.keys(val).find((key) => val[key]) || null;

export type NormalizedData = {
  [P in keyof DetectionSettings]: P extends "model"
    ? Record<string, boolean>
    : DetectionSettings[P];
};

const denormalizers = {
  model: denormalizeValue,
  confidence: (v: number) => (isNumber(v) ? roundNumber(v, 1) : v),
  overlay_draw_threshold: (v: number) => (isNumber(v) ? roundNumber(v, 1) : v),
};

export interface FieldsParams {
  debounce?: number;
  store?: ReturnType<typeof useDetectionStore>;
}

export interface DetectionFields {
  updateData: () => Promise<void>;
  updateDebounced: () => Promise<void>;
  fields: NormalizedData;
}

export const useDetectionFields = (params?: FieldsParams): DetectionFields => {
  const detectionStore = params?.store || useDetectionStore();

  const fields: NormalizedData = reactive({
    model: normalizeValue(detectionStore.data.model),
    img_size: detectionStore.data.img_size,
    active: detectionStore.data.active,
    confidence: detectionStore.data.confidence,
    labels: detectionStore.data.labels,
    overlay_draw_threshold: detectionStore.data.overlay_draw_threshold,
    overlay_style: detectionStore.data.overlay_style,
  });

  const updateData = async () => {
    const data = evolve(denormalizers, fields);
    const originalData = detectionStore.data;

    if (!isObjectEquals(originalData, data)) {
      await detectionStore.updateData(data);
    }
  };

  const updateDebounced = useAsyncDebounce(
    updateData,
    params?.debounce || 1000,
  );

  onMounted(() => {
    detectionStore.fetchModels();
  });

  watch(
    () => detectionStore.data,
    (newData) => {
      Object.entries(newData).forEach(([k, v]) => {
        const key = k as keyof typeof fields;
        if (key !== "model") {
          (fields as Record<string, any>)[key] = v;
        }
      });

      Object.keys(fields.model).forEach((k) => {
        fields.model[k] = newData.model === k;
      });

      if (newData.model) {
        fields.model[newData.model] = true;
      }
    },
  );

  return {
    updateData,
    updateDebounced,
    fields,
  };
};
