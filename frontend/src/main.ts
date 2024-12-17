import Aura from "@primevue/themes/aura";
import ConfirmationService from "primevue/confirmationservice";
import PrimeVue from "primevue/config";
import "primeicons/primeicons.css";
import "./assets/main.scss";
import { createApp } from "vue";
import { createPinia } from "pinia";

import { configPrimeVue } from "@/config/primevue";
import App from "./App.vue";
import router from "./router";

const app = createApp(App);

app.use(PrimeVue, {
  theme: {
    preset: Aura,
  },
});

app.use(ConfirmationService);
app.use(createPinia());
app.use(router);

configPrimeVue(app);
app.mount("#app");
