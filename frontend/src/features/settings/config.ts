import { generateMultiplesOf32 } from "@/util/number";
import { SettingsTab } from "@/features/settings/enums";

export const visibilitySettings = {
  text_info_view: {
    description: "Toggles text information on or off",
    label: "Gauges view",
  },
  speedometer_view: {
    label: "Speedometer",
    description: "Toggle the speedometer display on or off",
  },
  car_model_view: {
    description: "Toggles the 3D view of the car on or off",
    label: "3D view of the car",
  },
  text_to_speech_input: {
    description: "Toggle showing input for text to speech",
    label: "Text to speech input",
  },
  show_player: {
    description: "Toggle showing music player",
    label: "Music player",
  },
  show_object_detection_settings: {
    description: "Toggle showing object detection settings",
    label: "Object detection panel",
  },
};

export const behaviorSettings = {
  fullscreen: {
    description: "Toggle fullscreen",
    label: "Fullscreen",
  },
  auto_download_photo: {
    description: "Toggle auto-download of captured photos",
    label: "Auto-download photos",
  },
  auto_download_video: {
    description: "Toggle auto-download of recorded videos",
    label: "Auto-download videos",
  },
  auto_measure_distance_mode: {
    description: "Toggle auto-measure distance mode",
    label: "Auto-measure distance",
  },
  virtual_mode: {
    description: "Toggle replacing camera view with a 3D model",
    label: "Virtual 3D mode",
  },
};

export const ttsLanguages = [
  { label: "Afrikaans", value: "af" },
  { label: "Arabic", value: "ar" },
  { label: "Bengali", value: "bn" },
  { label: "Bosnian", value: "bs" },
  { label: "Catalan", value: "ca" },
  { label: "Czech", value: "cs" },
  { label: "Welsh", value: "cy" },
  { label: "Danish", value: "da" },
  { label: "German", value: "de" },
  { label: "Greek", value: "el" },
  { label: "English", value: "en" },
  { label: "English (Australia)", value: "en-au" },
  { label: "English (Canada)", value: "en-ca" },
  { label: "English (UK)", value: "en-gb" },
  { label: "English (Ghana)", value: "en-gh" },
  { label: "English (Ireland)", value: "en-ie" },
  { label: "English (India)", value: "en-in" },
  { label: "English (Nigeria)", value: "en-ng" },
  { label: "English (New Zealand)", value: "en-nz" },
  { label: "English (Philippines)", value: "en-ph" },
  { label: "English (Tanzania)", value: "en-tz" },
  { label: "English (UK)", value: "en-uk" },
  { label: "English (US)", value: "en-us" },
  { label: "English (South Africa)", value: "en-za" },
  { label: "Esperanto", value: "eo" },
  { label: "Spanish", value: "es" },
  { label: "Spanish (Spain)", value: "es-es" },
  { label: "Spanish (US)", value: "es-us" },
  { label: "Estonian", value: "et" },
  { label: "Finnish", value: "fi" },
  { label: "French", value: "fr" },
  { label: "French (Canada)", value: "fr-ca" },
  { label: "French (France)", value: "fr-fr" },
  { label: "Hindi", value: "hi" },
  { label: "Croatian", value: "hr" },
  { label: "Hungarian", value: "hu" },
  { label: "Armenian", value: "hy" },
  { label: "Indonesian", value: "id" },
  { label: "Icelandic", value: "is" },
  { label: "Italian", value: "it" },
  { label: "Japanese", value: "ja" },
  { label: "Javanese", value: "jw" },
  { label: "Khmer", value: "km" },
  { label: "Korean", value: "ko" },
  { label: "Latin", value: "la" },
  { label: "Latvian", value: "lv" },
  { label: "Macedonian", value: "mk" },
  { label: "Malayalam", value: "ml" },
  { label: "Marathi", value: "mr" },
  { label: "Myanmar (Burmese)", value: "my" },
  { label: "Nepali", value: "ne" },
  { label: "Dutch", value: "nl" },
  { label: "Norwegian", value: "no" },
  { label: "Polish", value: "pl" },
  { label: "Portuguese", value: "pt" },
  { label: "Portuguese (Brazil)", value: "pt-br" },
  { label: "Portuguese (Portugal)", value: "pt-pt" },
  { label: "Romanian", value: "ro" },
  { label: "Russian", value: "ru" },
  { label: "Sinhala", value: "si" },
  { label: "Slovak", value: "sk" },
  { label: "Albanian", value: "sq" },
  { label: "Serbian", value: "sr" },
  { label: "Sundanese", value: "su" },
  { label: "Swedish", value: "sv" },
  { label: "Swahili", value: "sw" },
  { label: "Tamil", value: "ta" },
  { label: "Telugu", value: "te" },
  { label: "Thai", value: "th" },
  { label: "Tagalog (Filipino)", value: "tl" },
  { label: "Turkish", value: "tr" },
  { label: "Ukrainian", value: "uk" },
  { label: "Vietnamese", value: "vi" },
  { label: "Chinese (Simplified)", value: "zh-cn" },
  { label: "Chinese (Traditional)", value: "zh-tw" },
];

export const NONE_KEY = "NONE";

export const saveableTabs = {
  [SettingsTab.GENERAL]: true,
  [SettingsTab.KEYBINDINGS]: false,
  [SettingsTab.CALIBRATION]: false,
  [SettingsTab.TTS]: false,
  [SettingsTab.PHOTOS]: false,
  [SettingsTab.MODELS]: true,
};

export const imgSizeOptions = generateMultiplesOf32(2000);
