import ConfirmationService from "primevue/confirmationservice";
import PrimeVue from "primevue/config";
import { createApp } from "vue";
import { configPrimeVue } from "@/config/primevue";
import { createPinia } from "pinia";
import "primeicons/primeicons.css";
import "./assets/main.scss";

import App from "./App.vue";
import router from "./router";
import { RoboPreset, pt } from "@/config/theme";

const app = createApp(App);

app.use(PrimeVue, {
  theme: {
    preset: RoboPreset,
  },
  pt,
});

app.use(ConfirmationService);
app.use(createPinia());
app.use(router);

configPrimeVue(app);
app.mount("#app");
