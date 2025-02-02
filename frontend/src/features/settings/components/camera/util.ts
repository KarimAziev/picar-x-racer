import { presetOptions } from "@/features/settings/components/camera/config";
import type { PresetOptionValue } from "@/features/settings/components/camera/config";
import { where, isShallowEq } from "@/util/func";
import { Nullable } from "@/util/ts-helpers";

export const findStepwisePreset = ({
  width,
  height,
}: Partial<{
  [P in keyof PresetOptionValue]: Nullable<PresetOptionValue[P]>;
}>) =>
  presetOptions.find((item) =>
    where({ width: isShallowEq(width), height: isShallowEq(height) })(
      item.value,
    ),
  );
