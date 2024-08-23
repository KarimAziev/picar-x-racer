import type { App } from "vue";

import StyleClass from "primevue/styleclass";
import Tooltip from "primevue/tooltip";

const configPrimeVue = function (app: App) {
  app.component("Button");
  app.directive("tooltip", Tooltip);
  app.directive("styleclass", StyleClass);
};

export { configPrimeVue };
