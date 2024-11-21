import { ref } from "vue";
import { useDetectionStore } from "@/features/controller/detectionStore";

export interface WebsocketStreamParams {
  reconnectDelay?: number;
  onOpen?: Function;
  onFirstMessage?: Function;
}

const extractFrameWithTimestamp = (data: ArrayBuffer) => {
  // Extract first 8 bytes for the timestamp (Double-precision float, 8 bytes)
  const timestampView = new DataView(data, 0, 8);
  const timestamp = timestampView.getFloat64(0, true);

  // The rest of the data is the frame
  const arrayBufferView = new Uint8Array(data, 8); // Skipping the first 8 bytes
  const blob = new Blob([arrayBufferView], { type: "image/jpeg" });

  return { timestamp, blob };
};

export const useWebsocketStream = (
  url: string,
  params?: WebsocketStreamParams,
) => {
  const { reconnectDelay, onOpen, onFirstMessage } = params || {};
  const detectionStore = useDetectionStore();
  const ws = ref<WebSocket>();
  const imgRef = ref<HTMLImageElement>();
  const imgInitted = ref(false);
  const imgLoading = ref(true);
  const connected = ref(false);
  const reconnectedEnabled = ref(true);
  const retryTimer = ref<NodeJS.Timeout | null>(null);
  const currentImageBlobUrl = ref<string>();

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
      ws.value.onopen = () => onOpen();
    }
    ws.value.binaryType = "arraybuffer";

    ws.value.onmessage = (wsMsg: MessageEvent) => {
      if (!connected.value) {
        if (onFirstMessage) onFirstMessage();
        connected.value = true;
      }

      const urlCreator = window.URL || window.webkitURL;
      if (currentImageBlobUrl.value) {
        urlCreator.revokeObjectURL(currentImageBlobUrl.value);
        currentImageBlobUrl.value = undefined;
      }

      const { timestamp, blob } = extractFrameWithTimestamp(wsMsg.data);
      const imageUrl = urlCreator.createObjectURL(blob);

      detectionStore.setCurrentFrameTimestamp(timestamp);
      if (imgRef.value) {
        imgRef.value.src = imageUrl;
        currentImageBlobUrl.value = imageUrl;
        if (imgInitted.value && imgLoading.value) {
          imgLoading.value = false;
        }
      }
    };

    ws.value.onclose = (_: CloseEvent) => {
      if (currentImageBlobUrl.value) {
        const urlCreator = window.URL || window.webkitURL;
        if (currentImageBlobUrl.value) {
          urlCreator.revokeObjectURL(currentImageBlobUrl.value);
        }

        currentImageBlobUrl.value = undefined;
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
