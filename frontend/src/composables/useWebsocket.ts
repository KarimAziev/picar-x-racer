import { ref, Ref } from "vue";
import { makeWebsocketUrl } from "@/util/url";

export interface WebSocketOptions {
  url: string;
  port?: number;
  onMessage?: (message: any) => void;
  onFirstMessage?: () => void;
  binaryType?: WebSocket["binaryType"];
  onOpen?: () => void;
  onClose?: () => void;
  onCleanup?: () => void;
  onError?: (error: Event) => void;
  retryInterval?: number;
  autoReconnect?: boolean;
  logPrefix?: string;
  isRetryable?: () => Promise<boolean>;
}

export interface WebSocketModel {
  initWS: () => void;
  send: (message: any) => void;
  closeWS: () => void;
  cleanup: () => void;
  retry: () => void;
  connected: Ref<boolean>;
  active: Ref<boolean>;
  loading: Ref<boolean>;
  reconnectEnabled: Ref<boolean>;
  ws: Ref<WebSocket | null>;
}

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
