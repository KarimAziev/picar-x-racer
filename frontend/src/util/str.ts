export const startCase = (str: string) =>
  str
    .trim()
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[-_]/g, " ")
    .split(" ")
    .map((v) => v[0].toUpperCase() + v.slice(1))
    .join(" ");
