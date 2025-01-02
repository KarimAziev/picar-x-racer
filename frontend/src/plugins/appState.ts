import { reactive } from "vue";
import type { App } from "vue";
import { isDarkMode } from "@/util/theme";

export default {
  install: (app: App) => {
    const _appState = reactive({ theme: "Aura", darkTheme: isDarkMode });

    app.config.globalProperties.$appState = _appState;
  },
};
