export type PresetOptionValue = {
  width: number;
  height: number;
};
export type PresetOption = {
  label: string;
  value: PresetOptionValue;
};

const sizes = {
  "32x32": "Icon size",
  "64x64": "Icon size (large)",
  "128x96": "4:3 (Thumbnail)",
  "160x120": "4:3 (Thumbnail)",
  "176x144": "QCIF (4:3)",
  "240x160": "3:2 (Small devices)",
  "320x180": "16:9 (Low resolution widescreen)",
  "320x240": "QVGA (4:3)",
  "352x288": "CIF (4:3)",
  "424x240": "16:9 (Widescreen SD)",
  "480x320": "3:2 (Small devices)",
  "640x360": "16:9 (SD widescreen)",
  "640x480": "VGA (4:3)",
  "800x600": "SVGA (4:3)",
  "848x480": "FWVGA+ (16:9)",
  "854x480": "FWVGA (16:9)",
  "960x540": "qHD (Quarter HD, 16:9)",
  "1024x768": "XGA (4:3)",
  "1280x720": "HD (720p, 16:9)",
  "1280x800": "WXGA (16:10)",
  "1440x900": "WXGA+ (16:10)",
  "1600x900": "HD+ (16:9)",
  "1920x1080": "Full HD (1080p, 16:9)",
  "1920x1200": "WUXGA (16:10)",
  "2048x1080": "2K (Digital cinema)",
  "2560x1440": "QHD (1440p, 16:9)",
  "2560x1600": "WQXGA (16:10)",
  "3840x2160": "UHD (4K, 16:9)",
  "4096x2160": "4K DCI (Digital cinema)",
  "5120x2880": "5K (16:9)",
  "7680x4320": "8K UHD (16:9)",
  "2592x1944": "4:3 (Canon PowerShot resolution)",
};

export const presetOptions: PresetOption[] = Object.entries(sizes).map(
  ([key, description]) => {
    const [width, height] = key.split("x");
    return {
      value: { width: +width, height: +height },
      label: description.length > 0 ? `${key}: ${description}` : key,
    };
  },
);
