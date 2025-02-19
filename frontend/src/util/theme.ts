export function isDarkMode() {
  const root = document.getElementsByTagName("html")[0];
  const className = "p-dark";
  return root.classList.contains(className);
}

export const normalizeThemeName = (themeName: string) => {
  const prefix = themeName.startsWith("--") ? "" : "--p-";

  const suffix = /-\d{2,3}$/.test(themeName) ? "" : "-500";

  return [prefix, themeName, suffix].join("");
};

export const getStyleVariable = (
  varname: string,
  styles: CSSStyleDeclaration,
) => {
  const value = styles.getPropertyValue(varname).trim();
  if (value.length > 0) {
    return value;
  }
};
