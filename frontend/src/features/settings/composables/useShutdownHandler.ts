import type { ConfirmationOptions } from "primevue/confirmationoptions";
import type { ButtonProps } from "primevue/button";
import { useConfirm } from "primevue/useconfirm";
import { usePopupStore } from "@/features/settings/stores";
import { useControllerStore } from "@/features/controller/store";

export interface ShutdownHandlerParams
  extends Omit<ConfirmationOptions, "accept" | "acceptProps"> {
  onAccept: () => void;
  acceptProps: ButtonProps;
}

export const useShutdownHandler = ({
  acceptProps,
  ...params
}: ShutdownHandlerParams) => {
  const controllerStore = useControllerStore();
  const confirmDialog = useConfirm();
  const popupStore = usePopupStore();

  const handleAccept = () => {
    popupStore.isOpen = false;
    controllerStore.resetAll();
    params.onAccept();
  };

  const handleConfirm = (event: MouseEvent) => {
    confirmDialog.require({
      target: event.currentTarget as HTMLElement,
      icon: "pi pi-power-off",
      rejectProps: {
        label: "Cancel",
        severity: "secondary",
        outlined: true,
      },
      modal: true,
      blockScroll: true,
      ...params,
      acceptProps: {
        severity: "danger",
        ...acceptProps,
      },
      accept: handleAccept,
    });
  };
  return {
    handleConfirm,
    confirmDialog,
    handleAccept,
  };
};
