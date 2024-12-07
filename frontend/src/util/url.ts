/**
 * Constructs a WebSocket URL given a specific path and an optional port.
 *
 * @param path - The path to append to the base URL.
 * @param port - (Optional) The port to use for the WebSocket connection. If not provided, the default port is used.
 * @returns The constructed WebSocket URL as a string.
 *
 * @example
 * // Example usage:
 * const wsUrl = makeWebsocketUrl('/api/socket');
 * console.log(wsUrl); // ws://localhost/api/socket (if protocol is http:)
 *
 * const secureWsUrl = makeWebsocketUrl('/secure-api/socket', 443);
 * console.log(secureWsUrl); // wss://localhost:443/secure-api/socket
 */
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

/**
 * Constructs an HTTP or HTTPS URL given a specific path and an optional port.
 *
 * @param path - The path to append to the base URL.
 * @param port - (Optional) The port to use for the HTTP/HTTPS connection. If not provided, the default port is used.
 * @returns The constructed HTTP/HTTPS URL as a string.
 *
 * @example
 * // Example usage:
 * const httpUrl = makeUrl('/api/resource');
 * console.log(httpUrl); // http://localhost/api/resource (if protocol is http:)
 *
 * const secureHttpUrl = makeUrl('/secure-api/resource', 443);
 * console.log(secureHttpUrl); // https://localhost:443/secure-api/resource
 */
export const makeUrl = (path: string, port?: number) => {
  const protocol = window.location.protocol === "https:" ? "https:" : "http:";
  const baseUrl = new URL(window.location.href);
  baseUrl.protocol = protocol;
  baseUrl.pathname = path;
  if (port) {
    baseUrl.port = `${port}`;
  }

  return baseUrl.toString();
};
