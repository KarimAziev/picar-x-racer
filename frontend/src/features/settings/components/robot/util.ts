import { isPlainObject } from "@/util/guards";
import { isObjectEquals } from "@/util/obj";

export const isCalibrationDataChanged = (
  storedData: any,
  localValue: any,
): boolean => {
  if (isPlainObject(storedData) && isPlainObject(localValue)) {
    if (storedData.calibration_offset !== storedData.saved_calibration_offset) {
      return true;
    }
    const found = Object.keys(storedData).find((key) =>
      isCalibrationDataChanged(storedData[key], localValue[key]),
    );
    return !!found;
  }
  return false;
};

export const isDataChangedPred = (
  storedData: any,
  localValue: any,
): boolean => {
  if (isPlainObject(storedData) && isPlainObject(localValue)) {
    return (
      isCalibrationDataChanged(storedData, localValue) ||
      !isObjectEquals(storedData, localValue)
    );
  }
  return false;
};
