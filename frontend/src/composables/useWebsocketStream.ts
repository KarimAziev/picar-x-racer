import { ref } from "vue";

export interface WebsocketStreamParams {
  reconnectDelay?: number;
  onOpen?: Function;
}

export const useWebsocketStream = (
  url: string,
  params?: WebsocketStreamParams,
) => {
  const { reconnectDelay, onOpen } = params || {};
  const ws = ref<WebSocket>();
  const imgRef = ref<HTMLImageElement>();
  const imgInitted = ref(false);
  const imgLoading = ref(true);
  const connected = ref(false);
  const reconnectedEnabled = ref(true);
  const retryTimer = ref<NodeJS.Timeout | null>(null);

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
      connected.value = true;
      const arrayBufferView = new Uint8Array(wsMsg.data);
      const blob = new Blob([arrayBufferView], { type: "image/jpeg" });
      const urlCreator = window.URL || window.webkitURL;
      const imageUrl = urlCreator.createObjectURL(blob);

      if (imgRef.value) {
        imgRef.value.src = imageUrl;
        if (imgInitted.value && imgLoading.value) {
          imgLoading.value = false;
        }
      }
    };

    ws.value.onclose = (_: CloseEvent) => {
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
