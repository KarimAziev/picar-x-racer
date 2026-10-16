// @vitest-environment jsdom

import PrimeVue from "primevue/config";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createApp,
  h,
  nextTick,
  reactive,
  type App,
  type Component,
} from "vue";
import { useStore as usePinoutStore, type PinMapping } from "../store";
import { normalizePins } from "../util";
import type { PinAssignment } from "../usage";
import PinChooser from "./PinChooser.vue";
import RobotConfig from "@/features/settings/components/robot/RobotConfig.vue";
import { useRobotStore } from "@/features/settings/stores";

const pins: PinMapping = {
  J8: {
    name: "J8",
    columns: 2,
    rows: 20,
    pins: {
      "37": {
        name: "GPIO26",
        gpio_number: 26,
        number: 37,
        row: 19,
        col: 1,
        names: ["GPIO26", "BCM26", "BOARD37", "D14"],
        interfaces: ["gpio"],
      },
      "16": {
        name: "GPIO23",
        gpio_number: 23,
        number: 16,
        row: 8,
        col: 2,
        names: ["GPIO23", "BCM23", "BOARD16", "D4"],
        interfaces: ["gpio"],
      },
      "6": {
        name: "GND",
        gpio_number: null,
        number: 6,
        row: 3,
        col: 2,
        names: ["GND", "BOARD6"],
        interfaces: [],
      },
    },
  },
};

const mounted: { app: App; container: HTMLElement }[] = [];

afterEach(() => {
  mounted.splice(0).forEach(({ app, container }) => {
    app.unmount();
    container.remove();
  });
  document.querySelector("#settings-footer")?.remove();
  localStorage.clear();
});

function mount(
  component: Component,
  props: Record<string, unknown>,
  pinia = createPinia(),
) {
  const store = usePinoutStore(pinia);
  store.$patch({ pins, ...normalizePins(pins), loaded: true });
  const container = document.createElement("div");
  document.body.append(container);
  const app = createApp({ setup: () => () => h(component, props) });
  app.use(pinia);
  app.use(PrimeVue, { unstyled: true });
  app.directive("tooltip", {});
  app.mount(container);
  mounted.push({ app, container });
  return container;
}

function gpioButton(root: ParentNode, gpio: number) {
  const button = root.querySelector<HTMLButtonElement>(
    `button[aria-label*="GPIO ${gpio},"]`,
  );
  if (!button) throw new Error(`GPIO ${gpio} button not found`);
  return button;
}

function description(button: HTMLButtonElement) {
  const id = button.getAttribute("aria-describedby");
  if (!id) throw new Error("Pin description is missing");
  const element = document.getElementById(id);
  if (!element) throw new Error("Pin description is not linked");
  return element.textContent;
}

describe("pin chooser assignments", () => {
  it("shows all owners and states, identifies this field, and keeps assigned GPIO selectable", async () => {
    const assignments: PinAssignment[] = [
      {
        key: '["motors",0,"enable_pin"]',
        owner: "Motors · Drive",
        field: "Enable",
        value: "BCM26",
        state: "enabled",
      },
      {
        key: '["servo","pin"]',
        owner: "Steering",
        field: "Pin",
        value: "BOARD37",
        state: "disabled",
      },
      {
        key: '["led","pin"]',
        owner: "Status LED",
        field: "Pin",
        value: 26,
        state: "configured",
      },
    ];
    const select = vi.fn();
    const container = mount(PinChooser, {
      modelValue: "D14",
      assignments,
      currentAssignmentKey: assignments[0].key,
      "onUpdate:modelValue": select,
    });
    await nextTick();
    const button = gpioButton(container, 26);
    expect(button.getAttribute("aria-pressed")).toBe("true");
    expect(button.disabled).toBe(false);
    expect(description(button)).toContain("3 assignments");
    for (const text of [
      "Motors · Drive",
      "Steering",
      "Status LED",
      "Enabled",
      "Disabled",
      "Configured",
      "This field",
    ]) {
      expect(description(button)).toContain(text);
    }
    button.click();
    expect(select).toHaveBeenCalledWith("D14");
    expect(description(gpioButton(container, 23))).toContain("Unassigned");
  });

  it("reacts to draft ownership changes without moving selection or reserving the old pin", async () => {
    const props = reactive({
      modelValue: 26,
      assignments: [
        {
          key: "motor",
          owner: "Drive",
          field: "Enable",
          value: 26,
          state: "enabled",
        } as PinAssignment,
      ],
    });
    const container = mount(PinChooser, props);
    props.assignments[0].value = "BOARD16";
    props.assignments[0].state = "disabled";
    await nextTick();
    expect(description(gpioButton(container, 26))).toContain("Unassigned");
    expect(gpioButton(container, 26).getAttribute("aria-pressed")).toBe("true");
    expect(description(gpioButton(container, 23))).toContain("Drive");
    expect(description(gpioButton(container, 23))).toContain("Disabled");
  });

  it("disables power pins natively and preserves physical pin order", async () => {
    const select = vi.fn();
    const container = mount(PinChooser, {
      modelValue: null,
      assignments: [],
      "onUpdate:modelValue": select,
    });
    await nextTick();
    const buttons = container.querySelectorAll<HTMLButtonElement>(
      "button[aria-pressed]",
    );
    expect([...buttons].map((button) => button.textContent?.trim())).toEqual([
      "GND",
      "GPIO23",
      "GPIO26",
    ]);
    expect(buttons[0].disabled).toBe(true);
    expect(description(buttons[0])).not.toContain("Unassigned");
    buttons[0].click();
    expect(select).not.toHaveBeenCalled();
  });

  it("does not claim pins are unassigned when configuration context is unavailable", async () => {
    const container = mount(PinChooser, { modelValue: 26 });
    await nextTick();
    expect(container.textContent).not.toContain("Unassigned");
  });

  it("reports unmatched configured pins instead of silently omitting them", async () => {
    const container = mount(PinChooser, {
      modelValue: "26",
      assignments: [
        {
          key: "servo",
          owner: "Steering",
          field: "Pin",
          value: "unknown",
          state: "disabled",
        },
      ],
    });
    await nextTick();
    expect(gpioButton(container, 26).getAttribute("aria-pressed")).toBe("true");
    const message = container.querySelector('[role="status"]')?.textContent;
    expect(message).toContain("could not be matched");
    expect(message).toContain("Steering · Pin: unknown");
  });

  it("uses the unsaved robot form through the schema field and dialog", async () => {
    const pinia = createPinia();
    const robot = useRobotStore(pinia);
    robot.data.motors = [
      {
        ...robot.data.motors[0],
        dir_pin: 26,
        name: "Rear drive",
        enabled: true,
      },
    ];
    robot.data.led = { ...robot.data.led, name: "Status light", pin: 26 };
    const pinSchema = {
      title: "Pin",
      "x-ui-type": "pin" as const,
      anyOf: [{ type: "integer" as const }, { type: "string" as const }],
    };
    robot.config = {
      type: "object",
      properties: {
        motors: {
          type: "array",
          title: "Motors",
          minItems: 1,
          items: {
            type: "object",
            properties: {
              enabled: { type: "boolean", title: "Enabled" },
              name: { type: "string", title: "Name" },
              dir_pin: pinSchema,
            },
          },
        },
        led: { type: "object", title: "LED", properties: { pin: pinSchema } },
      },
    };
    const footer = document.createElement("div");
    footer.id = "settings-footer";
    document.body.append(footer);
    const container = mount(RobotConfig, { idPrefix: "robot-test" }, pinia);
    await nextTick();

    async function open(value: string) {
      const button = [...container.querySelectorAll("button")].find(
        (button) => button.textContent?.trim() === value,
      );
      if (!button) throw new Error(`Pin field ${value} not found`);
      button.click();
      await nextTick();
      const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
      if (!dialog) throw new Error("Pin dialog not open");
      return dialog;
    }

    let dialog = await open("GPIO26");
    expect(description(gpioButton(dialog, 26))).toContain("2 assignments");
    expect(description(gpioButton(dialog, 26))).toContain("Rear drive");
    expect(description(gpioButton(dialog, 26))).toContain("Status light");
    expect(description(gpioButton(dialog, 26))).toContain("This field");
    gpioButton(dialog, 23).click();
    await nextTick();

    const toggle = container.querySelector<HTMLInputElement>(
      'input[role="switch"]',
    );
    if (!toggle) throw new Error("Motor enable switch not found");
    toggle.click();
    await nextTick();
    dialog = await open("GPIO23");
    expect(description(gpioButton(dialog, 23))).toContain("Rear drive");
    expect(description(gpioButton(dialog, 23))).toContain("Disabled");
    expect(description(gpioButton(dialog, 23))).toContain("This field");
    expect(description(gpioButton(dialog, 26))).not.toContain("Rear drive");
    expect(description(gpioButton(dialog, 26))).toContain("Status light");
    expect(robot.data.motors[0].dir_pin).toBe(26);
    expect(robot.data.motors[0].enabled).toBe(true);
  });
});
