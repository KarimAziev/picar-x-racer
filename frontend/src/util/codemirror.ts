import { languages } from "@codemirror/language-data";
import type { First } from "@/util/ts-helpers";

export const getFileExtension = (filename: string) => {
  const baseNameIdx = filename.lastIndexOf("/");
  const basename =
    baseNameIdx !== -1 ? filename.slice(baseNameIdx + 1) : filename;
  const extIdx = basename.lastIndexOf(".");
  const ext = extIdx !== -1 ? basename.slice(extIdx + 1) : "";
  return ext;
};

export const getFileNameBase = (filename: string) => {
  const baseNameIdx = filename.lastIndexOf("/");
  const basename =
    baseNameIdx !== -1 ? filename.slice(baseNameIdx + 1) : filename;
  return basename;
};

export const findLang = (filename: string) => {
  const filenameBase = getFileNameBase(filename);

  const fileExt = getFileExtension(filenameBase);
  const result = languages.find(
    (lang) =>
      lang.extensions.includes(fileExt) || lang.filename?.test(filenameBase),
  );
  return result;
};

export const getLanguageOptions = () =>
  languages.map((lang) => ({ value: lang.name, label: lang.name }));

export const mapLanguagesHash = () => {
  const hash = new Map<string, First<typeof languages>>();
  languages.forEach((l) => {
    hash.set(l.name, l);
  });
  return hash;
};
