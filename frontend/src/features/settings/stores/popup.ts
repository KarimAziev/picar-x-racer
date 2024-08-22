import { defineStore } from "pinia";
import { SettingsTab } from "@/features/settings/enums";

export interface State {
  isOpen: boolean;
  tab?: SettingsTab;
  isKeyRecording?: boolean;
}

const defaultState: State = {
  isOpen: false,
  tab: SettingsTab.GENERAL,
};

export const useStore = defineStore("popup-dialog", {
  state: () => ({ ...defaultState }),
});
