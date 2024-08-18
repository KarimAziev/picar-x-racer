<template>
  <div class="speedometer" ref="speedometerRef">
    <div class="gauge">
      <div class="progress"></div>
      <div class="gauge-center"></div>
      <div class="needle" ref="needleRef"></div>
    </div>
    <div class="labels">
      <div class="center-label" ref="centerLabelRef">{{ adjustedValue }}</div>
    </div>
    <div class="outer-labels" ref="outerLabelsRef">
      <div v-for="label in outerLabels" :key="label.value" :style="label.style">
        {{ label.value }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

export interface SpeedometerParams {
  value: number
  minValue: number
  maxValue: number
  segments: number
}

const props = defineProps<SpeedometerParams>()
const speedometerRef = ref<HTMLElement | null>(null)
const needleRef = ref<HTMLElement | null>(null)
const centerLabelRef = ref<HTMLElement | null>(null)
const outerLabelsRef = ref<HTMLElement | null>(null)

const adjustedValue = computed(() => {
  return Math.max(props.minValue, Math.min(props.value, props.maxValue))
})

const renderOuterLabels = () => {
  const labels = []
  for (let i = 0; i <= props.segments; i++) {
    const step = (props.maxValue - props.minValue) / props.segments
    const value = step * i
    const rotation = 180 + i * (180 / props.segments)
    labels.push({
      value,
      style: `transform: rotate(${rotation}deg) translateY(-120px) rotate(-${rotation}deg);`
    })
  }
  return labels
}

const outerLabels = renderOuterLabels()

const updateNeedle = (value: number) => {
  if (needleRef.value && centerLabelRef.value) {
    const rotation = ((value - props.minValue) / (props.maxValue - props.minValue)) * 180 - 90
    needleRef.value.style.transform = `translateY(-100%) rotate(${rotation + 180}deg)`
    centerLabelRef.value.textContent = `${value}`
  }
}

watch(
  () => props.value,
  (newValue) => {
    updateNeedle(newValue)
  }
)

onMounted(() => {
  if (speedometerRef.value) {
    updateNeedle(adjustedValue.value)
  }
})
</script>

<style scoped>
@import '/src/assets/scss/variables.scss';

.speedometer {
  position: relative;
  width: 300px;
  height: 300px;
}

.gauge {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  position: relative;
  overflow: hidden;
}

.gauge::before {
  content: '';
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 10px solid #00ffff;
  opacity: 0.5;
  background: rgba(0, 0, 0, 0.4);
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
}

.gauge-center {
  width: 120px;
  height: 120px;
  background: #00ffff;
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
    lime 0 90deg,
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
  color: #00ffff;
  font-size: 2rem;
  position: absolute;
  bottom: 40%;
  right: 10%;
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

.outer-labels div {
  position: absolute;
  width: 2rem;
  height: 2rem;
  text-align: center;
  transform-origin: bottom center;
  color: #00ffff;
}
</style>
