import { createApp } from "vue";
import PrimeVue from "primevue/config";
import ConfirmationService from "primevue/confirmationservice";
import DialogService from "primevue/dialogservice";
import ToastService from "primevue/toastservice";
import { configPrimeVue } from "@/config/primevue";
import { createPinia } from "pinia";
import { RoboPreset } from "@/config/theme";
import App from "@/App.vue";
import router from "@/router";
import "primeicons/primeicons.css";

import "./assets/main.css";

import { pt } from "@/config/theme";

const app = createApp(App);

app.use(PrimeVue, {
  theme: {
    preset: RoboPreset,
    options: {
      prefix: "p",
      darkModeSelector: ".p-dark",
    },
  },
  pt,
});

app.use(createPinia());
app.use(ConfirmationService);
app.use(ToastService);
app.use(DialogService);
app.use(router);
configPrimeVue(app);

app.mount("#app");
