import { presetOptions } from "@/features/settings/components/camera/config";
import type { PresetOptionValue } from "@/features/settings/components/camera/config";
import { where, isShallowEq } from "@/util/func";

export const findStepwisePreset = ({
  width,
  height,
}: Partial<PresetOptionValue>) =>
  presetOptions.find((item) =>
    where({ width: isShallowEq(width), height: isShallowEq(height) })(
      item.value,
    ),
  );
