export const wait = async (delay: number) =>
  new Promise((resolve) => setTimeout(resolve, delay));
