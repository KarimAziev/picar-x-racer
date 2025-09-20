<template>
  <div
    class="speedometer"
    ref="speedometerRef"
    :class="class"
    :style="styleObj"
  >
    <div class="gauge">
      <div class="progress"></div>
      <div class="gauge-center" :style="gaugeCenterStyle"></div>
      <div class="needle" ref="needleRef"></div>
    </div>
    <div class="labels">
      <span class="center-label" ref="centerLabelRef">
        {{ adjustedValue }}
      </span>
      <template v-if="$slots.extra">
        <span class="extra-info">
          <slot name="extra" />
        </span>
      </template>
    </div>
    <div class="outer-labels">
      <span
        v-for="label in outerLabels"
        :key="label.value"
        :style="label.style"
        :class="{
          disabled: !!label.disabled,
        }"
      >
        {{ label.value }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, reactive } from "vue";
import { roundNumber } from "@/util/number";

export interface SpeedometerParams {
  value: number;
  minValue: number;
  maxValue: number;
  segments: number;
  disabledThreshold?: number;
  class?: string;
  size?: number;
  maxAngle?: number;
}

const props = defineProps<SpeedometerParams>();
const speedometerRef = ref<HTMLElement | null>(null);
const needleRef = ref<HTMLElement | null>(null);
const centerLabelRef = ref<HTMLElement | null>(null);

const adjustedValue = computed(() => props.value);

const rotationStep = computed(() => (props.maxAngle || 210) / props.segments);

const defaultSize = 300;
const translateY = computed(() => {
  const actualHeight = props.size || defaultSize;
  return actualHeight * (120 / 300);
});

const styleObj = computed(() => ({
  width: `${props.size || defaultSize}px`,
  height: `${props.size || defaultSize}px`,
}));

const gaugeCenterStyle = reactive({
  width: `${translateY.value}px`,
  height: `${translateY.value}px`,
});

const outerLabels = computed(() => {
  const labels: {
    value: number;
    style: string;
    disabled: boolean | 0 | undefined;
  }[] = [];
  for (let i = 0; i <= props.segments; i++) {
    const step = (props.maxValue - props.minValue) / props.segments;

    const value = step * i;
    const rotation = 180 + i * rotationStep.value;
    const disabled = props.disabledThreshold && props.disabledThreshold < value;
    labels.push({
      value: roundNumber(value),
      style: `transform: rotate(${rotation}deg) translateY(${-translateY.value}px) rotate(-${rotation}deg);`,
      disabled,
    });
  }
  return labels;
});

const updateNeedle = (value: number) => {
  if (needleRef.value && centerLabelRef.value) {
    const absVal = Math.abs(value);
    const step = (props.maxValue - props.minValue) / props.segments;

    const rotation = ((absVal - props.minValue) / step) * rotationStep.value;

    needleRef.value.style.transform = `translateY(-100%) rotate(${rotation + 90}deg)`;
  }
};

watch(
  () => props.value,
  (newValue) => {
    updateNeedle(newValue);
  },
);

onMounted(() => {
  if (speedometerRef.value) {
    updateNeedle(adjustedValue.value);
  }
});
</script>

<style scoped>
.speedometer {
  position: relative;
  color: var(--color-text);
  pointer-events: none;
}

.gauge {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  position: relative;
  overflow: hidden;
}

.gauge::before {
  content: "";
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 10px solid var(--robo-color-primary);
  opacity: 0.5;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
}

.gauge-center {
  background: var(--color-text);
  opacity: 0.2;
  border-radius: 50%;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 3;
}

.progress {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(135deg);
  width: 150%;
  height: 150%;
  background: conic-gradient(
    transparent 0 135deg,
    transparent 135deg 270deg,
    var(--color-text) 0 90deg,
    rgba(0, 0, 0, 0.4) 90deg 135deg
  );
  border-radius: 50%;
  z-index: 2;
}

.needle {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 45%;
  height: 2px;
  background: lightcoral;
  transform-origin: left;
  transform: translateX(-50%) rotate(0deg);
  z-index: 3;
  transition: transform 0.3s ease;
}

.labels {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  z-index: 10;
}

.center-label {
  font-size: 2rem;
  position: absolute;
  bottom: 40%;
  right: 10%;
}

.extra-info {
  font-size: 1rem;
  position: absolute;
  bottom: 21%;
  right: 14%;
}

.outer-labels {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  z-index: 10;
}

.outer-labels span {
  position: absolute;
  width: 2rem;
  height: 2rem;
  text-align: center;
  transform-origin: bottom center;
  color: var(--color-text);
}

.disabled {
  opacity: 0.5;
}
</style>
