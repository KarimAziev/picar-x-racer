// @vitest-environment jsdom
import { createApp, nextTick } from "vue";
import PrimeVue from "primevue/config";
import { beforeEach, describe, expect, it } from "vitest";
import Fieldset from "@/ui/Fieldset.vue";
beforeEach(() => localStorage.clear());
describe("persistent collapsible fieldsets", () => {
  it("remembers a toggle when no initial collapsed value was supplied", async () => {
    const root = document.createElement("div");
    const mount = () => {
      const app = createApp(Fieldset, {
        id: "fieldset-test",
        legend: "Settings",
      });
      app.use(PrimeVue);
      app.mount(root);
      return app;
    };
    let app = mount();
    root.querySelector<HTMLElement>("[aria-expanded]")?.click();
    await nextTick();
    expect(localStorage.getItem("fieldset-test")).toBe("true");
    app.unmount();
    app = mount();
    expect(
      root.querySelector("[aria-expanded]")?.getAttribute("aria-expanded"),
    ).toBe("false");
    app.unmount();
  });
});
