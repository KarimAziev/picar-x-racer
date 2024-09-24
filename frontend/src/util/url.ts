export const makeWebsocketUrl = (path: string) => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const baseUrl = new URL(window.location.href);
  baseUrl.protocol = protocol;
  baseUrl.pathname = path;

  return baseUrl.toString();
};
