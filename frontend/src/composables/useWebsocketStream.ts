import { ref } from "vue";

export interface WebsocketStreamParams {
  reconnectDelay?: number;
  onOpen?: Function;
  onFirstMessage?: Function;
}

export const useWebsocketStream = (
  url: string,
  params?: WebsocketStreamParams,
) => {
  const { reconnectDelay, onOpen, onFirstMessage } = params || {};
  const ws = ref<WebSocket>();
  const imgRef = ref<HTMLImageElement>();
  const imgInitted = ref(false);
  const imgLoading = ref(true);
  const connected = ref(false);
  const reconnectedEnabled = ref(true);
  const retryTimer = ref<NodeJS.Timeout | null>(null);
  const currentImageUrl = ref<string>();

  const handleImageOnLoad = () => {
    imgLoading.value = false;
    imgInitted.value = true;
  };

  const initWS = () => {
    ws.value = new WebSocket(url);
    if (!ws.value) {
      return;
    }
    if (onOpen) {
      ws.value.onopen = () => {
        onOpen();
      };
    }
    ws.value.binaryType = "arraybuffer";

    ws.value.onmessage = (wsMsg: MessageEvent) => {
      if (!connected.value) {
        if (onFirstMessage) {
          onFirstMessage();
        }
        connected.value = true;
      }

      const urlCreator = window.URL || window.webkitURL;
      if (currentImageUrl.value) {
        urlCreator.revokeObjectURL(currentImageUrl.value);
      }

      const arrayBufferView = new Uint8Array(wsMsg.data);
      const blob = new Blob([arrayBufferView], { type: "image/jpeg" });

      const imageUrl = urlCreator.createObjectURL(blob);

      if (imgRef.value) {
        imgRef.value.src = imageUrl;
        currentImageUrl.value = imageUrl;
        if (imgInitted.value && imgLoading.value) {
          imgLoading.value = false;
        }
      }
    };

    ws.value.onclose = (_: CloseEvent) => {
      if (currentImageUrl.value) {
        const urlCreator = window.URL || window.webkitURL;
        urlCreator.revokeObjectURL(currentImageUrl.value);
        currentImageUrl.value = undefined;
      }
      connected.value = false;
      imgLoading.value = true;
      retryConnection();
    };
  };

  const retryConnection = () => {
    if (retryTimer.value) {
      clearTimeout(retryTimer.value);
    }
    if (reconnectedEnabled.value && !connected.value) {
      retryTimer.value = setTimeout(() => {
        console.log("Retrying WebSocket connection...");
        initWS();
      }, reconnectDelay || 5000);
    }
  };

  const closeWS = () => {
    reconnectedEnabled.value = false;
    if (ws.value) {
      ws.value.close();
    }
  };

  return {
    initWS,
    closeWS,
    handleImageOnLoad,
    imgRef,
    imgInitted,
    imgLoading,
    reconnectedEnabled,
    retryTimer,
    connected,
  };
};
