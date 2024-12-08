import { defineStore } from "pinia";
import { SettingsTab } from "@/features/settings/enums";

export interface State {
  isOpen: boolean;
  tab: SettingsTab;
  isKeyRecording?: boolean;
  isPreviewImageOpen: boolean;
}

const defaultState: State = {
  isOpen: false,
  tab: SettingsTab.GENERAL,
  isPreviewImageOpen: false,
};

export const useStore = defineStore("popup-dialog", {
  state: () => ({ ...defaultState }),
});
