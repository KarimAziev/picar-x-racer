export const makeWebsocketUrl = (path: string, port?: number) => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const baseUrl = new URL(window.location.href);
  baseUrl.protocol = protocol;
  baseUrl.pathname = path;
  if (port) {
    baseUrl.port = `${port}`;
  }

  return baseUrl.toString();
};
