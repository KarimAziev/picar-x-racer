import type { InjectionKey, Ref } from "vue";
import type { PinAssignment } from "@/features/pinout/usage";

/** Assignments in the current robot-settings draft, including unsaved edits. */
export const pinAssignmentsKey: InjectionKey<Readonly<Ref<PinAssignment[]>>> =
  Symbol("robot-pin-assignments");
