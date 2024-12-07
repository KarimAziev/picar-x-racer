import { ref } from "vue";
import type { Ref } from "vue";
import { makeWebsocketUrl } from "@/util/url";

/**
 * Options for configuring the WebSocket connection.
 */
export interface WebSocketOptions {
  /** The WebSocket server URL. */
  url: string;
  /** An optional port number for the WebSocket connection. */
  port?: number;
  /** A callback invoked when a message is received from the WebSocket. */
  onMessage?: (message: any) => void;
  /** A callback invoked when the first message is received from the WebSocket. */
  onFirstMessage?: () => void;
  /** The binary type of the WebSocket (e.g., "arraybuffer"). */
  binaryType?: WebSocket["binaryType"];
  /** A callback invoked when the WebSocket connection is opened. */
  onOpen?: () => void;
  /** A callback invoked when the WebSocket connection is closed. */
  onClose?: () => void;
  /** A callback invoked during the cleanup process. */
  onCleanup?: () => void;
  /** A callback invoked when an error occurs on the WebSocket. */
  onError?: (error: Event) => void;
  /** The interval (in milliseconds) to retry the connection if it fails. */
  retryInterval?: number;
  /** Whether the WebSocket should automatically attempt reconnections. */
  autoReconnect?: boolean;
  /** A log prefix for identifying WebSocket logs. */
  logPrefix?: string;
  /** A function that determines whether retries are allowed. */
  isRetryable?: () => Promise<boolean>;
}

/**
 * Model representing the WebSocket and associated state/methods.
 */
export interface WebSocketModel {
  /** Initializes the WebSocket connection. */
  initWS: () => void;
  /** Sends a message through the WebSocket connection. */
  send: (message: any) => void;
  /** Closes the WebSocket connection. */
  closeWS: () => void;
  /** Cleans up the WebSocket resources (e.g., closing the connection). */
  cleanup: () => void;
  /** Attempts to retry the WebSocket connection. */
  retry: () => void;
  /** Tracks whether the WebSocket is currently connected. */
  connected: Ref<boolean>;
  /** Tracks whether the WebSocket is actively handling messages. */
  active: Ref<boolean>;
  /** Tracks whether the WebSocket is in the process of connecting or retrying. */
  loading: Ref<boolean>;
  /** Indicates whether reconnection attempts are enabled. */
  reconnectEnabled: Ref<boolean>;
  /** Holds the current WebSocket instance or null if not connected. */
  ws: Ref<WebSocket | null>;
}

/**
 * A composable function for managing a WebSocket connection in a Vue application.
 *
 * @param options - Configuration options for the WebSocket connection.
 * @returns The WebSocket model to manage the connection and state.
 */
export function useWebSocket(options: WebSocketOptions): WebSocketModel {
  const ws = ref<WebSocket | null>(null);
  const retryTimer = ref<NodeJS.Timeout | null>(null);
  const loading = ref(false);
  const active = ref(false);
  const connected = ref(false);
  const reconnectEnabled = ref(options.autoReconnect ?? true);
  const retryInterval = options.retryInterval ?? 5000;
  const messageQueue = ref<string[]>([]);

  const logPrefix = options.logPrefix || options.url;

  const logMessages = {
    close: [logPrefix, `WebSocket connection closed`]
      .filter((v) => !!v)
      .join(" "),
    error: [logPrefix, `WebSocket error: `].filter((v) => !!v).join(" "),
    retrying: [logPrefix, `Retrying connection...`]
      .filter((v) => !!v)
      .join(" "),
  };

  const handleOnMessage = (event: MessageEvent) => {
    if (options.onMessage) {
      options.onMessage(event.data);
    }
  };

  const handleOnJSONMessage = (event: MessageEvent) => {
    if (options.onMessage) {
      options.onMessage(JSON.parse(event.data));
    }
  };

  const messageHandler =
    options.binaryType === "arraybuffer"
      ? handleOnMessage
      : handleOnJSONMessage;

  const initWS = () => {
    if (connected.value) {
      return;
    }

    if (options.autoReconnect) {
      reconnectEnabled.value = true;
    }

    loading.value = true;

    ws.value = new WebSocket(makeWebsocketUrl(options.url, options.port));

    if (options.binaryType) {
      ws.value.binaryType = options.binaryType;
    }

    ws.value.onopen = () => {
      loading.value = false;
      connected.value = true;
      if (options.onOpen) {
        options.onOpen();
      }

      while (messageQueue.value.length > 0) {
        ws.value?.send(messageQueue.value.shift()!);
      }
    };
    ws.value.onmessage = (event) => {
      if (!active.value) {
        if (options.onFirstMessage) {
          options.onFirstMessage();
        }
        active.value = true;
      }

      messageHandler(event);
    };

    ws.value.onerror = (error) => {
      console.error(logMessages.error, error.type);
      if (options.onError) {
        options.onError(error);
      }
      connected.value = false;
      loading.value = false;
    };

    ws.value.onclose = async () => {
      console.log(logMessages.close);
      if (options.onClose) {
        options.onClose();
      }
      connected.value = false;
      active.value = false;
      loading.value = false;

      await retry();
    };
  };

  const retry = async () => {
    if (retryTimer.value) {
      clearTimeout(retryTimer.value);
    }
    if (options.isRetryable) {
      try {
        reconnectEnabled.value = await options.isRetryable();
      } catch (error) {
        reconnectEnabled.value = false;
      }
    }
    if (reconnectEnabled.value && !connected.value) {
      retryTimer.value = setTimeout(() => {
        console.log(logMessages.retrying);
        if (reconnectEnabled.value && !connected.value) {
          initWS();
        }
      }, retryInterval);
    }
  };

  const send = (message: any) => {
    const msgString = JSON.stringify(message);
    if (connected.value) {
      ws.value?.send(msgString);
    } else {
      messageQueue.value.push(msgString);
    }
  };

  const closeWS = () => {
    if (retryTimer.value) {
      clearTimeout(retryTimer.value);
    }
    reconnectEnabled.value = false;
    ws.value?.close();
  };

  const cleanup = () => {
    if (options.onCleanup) {
      options.onCleanup();
    }
    closeWS();
    messageQueue.value = [];
  };

  return {
    initWS,
    send,
    closeWS,
    cleanup,
    retry,
    connected,
    active,
    loading,
    reconnectEnabled,
    ws,
  };
}
