import { defineStore } from "pinia";
import { SettingsTab } from "@/features/settings/enums";

export interface State {
  isOpen: boolean;
  tab: SettingsTab;
  isKeyRecording?: boolean;
  isPreviewImageOpen: boolean;
  isEscapable: boolean;
}

const defaultState: State = {
  isOpen: false,
  tab: SettingsTab.GENERAL,
  isPreviewImageOpen: false,
  isEscapable: true,
};

export const useStore = defineStore("popup-dialog", {
  state: () => ({ ...defaultState }),
});
