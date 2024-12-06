<template>
  <div class="p-field" :class="classObject">
    <span class="label" v-if="label" :class="labelClassName"
      >{{ label }}
      <span v-if="message" class="message">
        {{ message }}
      </span>
    </span>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

export type Props = {
  message?: string;
  label?: string;
  fieldClassName?: string;
  labelClassName?: string;
  layout?: "col" | "row-reverse" | "row" | "col-reverse";
};

const props = defineProps<Props>();

const classObject = computed(() => ({
  [props.layout ? props.layout : "col"]: true,
  [props.fieldClassName ? props.fieldClassName : ""]: !!props.fieldClassName,
}));
</script>
<style scoped lang="scss">
.label {
  font-weight: bold;
  position: relative;
  display: flex;
  flex-direction: column;
  .message {
    background-color: transparent;
    color: var(--red-400);
  }
}
@import "./field.scss";
:deep(.p-select-dropdown),
:deep(.p-treeselect-dropdown) {
  width: 0.8rem;

  .p-icon {
    position: relative;
    width: 0.5rem;
    right: 50%;
  }
}
:deep(.p-inputtext),
:deep(.p-treeselect),
:deep(.p-select),
:deep(.p-inputnumber) {
  display: flex;
  align-items: center;
  max-width: 140px;
  height: 30px;

  @media (min-width: 576px) {
    height: 35px;
    max-width: 140px;
  }
  @media (min-width: 768px) {
    max-width: 190px;
  }

  @media (min-width: 992px) {
    max-width: 210px;
  }
  @media (min-width: 1200px) {
    height: 40px;
    max-width: 220px;
  }

  @media (min-width: 1440px) {
    max-width: 230px;
  }

  @media (min-width: 1600px) {
    max-width: 240px;
  }
}

/* :deep(.p-select-label) { */
/*   padding: 0.2rem 0.4rem; */

/*   @media (min-width: 576px) { */
/*     padding: 0.25rem 0.7rem; */
/*   } */

/*   @media (min-width: 768px) { */
/*     padding: 0.3rem 0.7rem; */
/*   } */

/*   @media (min-width: 1200px) { */
/*     padding: 0.4rem 0.7rem; */
/*   } */
/* } */
</style>
