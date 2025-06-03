import { definePreset } from "@primevue/themes";
import Aura from "@primevue/themes/aura";
import { preset } from "@/presets/RoboPreset";

export const RoboPreset = definePreset(Aura, preset);

export const pt = {
  treeselect: {
    dropdownIcon: {
      class: "pr-2 pt-1",
    },
  },
  inputnumber: {
    decrementIcon: {
      class: "p-1 relative bottom-[6px]",
    },
    incrementIcon: {
      class: "p-1",
    },
  },
  select: {
    root: {
      class: "select-root",
    },
    dropdown: {
      class: "pr-3 pt-1 md:pt-1.5 pl-1",
    },
  },
  cascadeselect: {
    optionList: {
      class: "cascade-select",
    },
  },
};
