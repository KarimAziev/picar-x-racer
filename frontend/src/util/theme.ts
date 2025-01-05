export function isDarkMode() {
  const root = document.getElementsByTagName("html")[0];
  const className = "p-dark";
  return root.classList.contains(className);
}
