import type { App } from "vue";

import ConfirmationService from "primevue/confirmationservice";
import StyleClass from "primevue/styleclass";
import ToastService from "primevue/toastservice";
import Tooltip from "primevue/tooltip";

const configPrimeVue = function (app: App) {
  app.component("Button");
  app.directive("tooltip", Tooltip);
  app.directive("styleclass", StyleClass);

  app.use(ToastService);
  app.use(ConfirmationService);
};

export { configPrimeVue };
