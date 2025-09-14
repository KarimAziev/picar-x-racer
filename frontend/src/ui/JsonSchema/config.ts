import { defineComponents } from "@/util/vue-helpers";
import CalibrationOffset from "@/features/settings/components/calibration/CalibrationOffset.vue";
import MotorDirection from "@/features/settings/components/calibration/MotorDirection.vue";
import NumberInputField from "@/ui/NumberInputField.vue";
import SelectField from "@/ui/SelectField.vue";
import StringOrNumberField from "@/ui/StringOrNumberField.vue";
import TextField from "@/ui/TextField.vue";
import ToggleSwitchField from "@/ui/ToggleSwitchField.vue";
import { FieldType } from "@/ui/JsonSchema/interface";
import PinChooserDialog from "@/features/pinout/components/PinChooserDialog.vue";

export const simpleTypes: Partial<Record<FieldType, boolean>> = {
  string: true,
  boolean: true,
  number: true,
};

export const componentsWithDefaults = defineComponents(
  {
    integer: NumberInputField,
    string: TextField,
    string_or_number: StringOrNumberField,
    number: NumberInputField,
    boolean: ToggleSwitchField,
    hex: StringOrNumberField,
    motor_direction: MotorDirection,
    select: SelectField,
    calibration_offset: CalibrationOffset,
    pin: PinChooserDialog,
  },
  {
    integer: {
      step: 1,
      maxFractionDigits: 0,
    },
    string: {
      fieldClassName: "w-full",
    },
    calibration_offset: {},
    number: {
      step: 0.1,
      minFractionDigits: 1,
    },
    string_or_number: {
      inputClassName: "!w-full",
      integerProps: { min: 1 },
      stringProps: { min: 1 },
    },
    boolean: {},
    hex: {
      integerProps: { min: 1 },
      stringProps: { min: 1 },
      inputClassName: "!w-full",
      hex: true,
    },

    motor_direction: {},
    select: {},
    pin: {},
  },
);

export const renameMap = {
  const: "readonly",
};
