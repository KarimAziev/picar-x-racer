import { ref } from "vue";
import { useWebSocket, WebSocketOptions } from "@/composables/useWebsocket";
import { useDetectionStore } from "@/features/detection";

export interface WebsocketStreamParams {
  retryInterval?: number;
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

export const useWebsocketStream = (params: WebSocketOptions) => {
  const detectionStore = useDetectionStore();
  const imgRef = ref<HTMLImageElement>();
  const imgInitted = ref(false);
  const imgLoading = ref(true);
  const currentImageBlobUrl = ref<string>();

  const handleImageOnLoad = () => {
    imgLoading.value = false;
    imgInitted.value = true;
  };

  const handleOnMessage = (data: MessageEvent["data"]) => {
    if (params.onMessage) {
      params.onMessage(data);
    }
    const urlCreator = window.URL || window.webkitURL;
    if (currentImageBlobUrl.value) {
      urlCreator.revokeObjectURL(currentImageBlobUrl.value);
      currentImageBlobUrl.value = undefined;
    }

    const { timestamp, blob } = extractFrameWithTimestamp(data);

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

  const handleOnClose = () => {
    if (params.onClose) {
      params.onClose();
    }
    if (currentImageBlobUrl.value) {
      const urlCreator = window.URL || window.webkitURL;
      urlCreator.revokeObjectURL(currentImageBlobUrl.value);

      currentImageBlobUrl.value = undefined;
    }
    imgLoading.value = true;
  };

  const {
    ws,
    initWS,
    send,
    closeWS,
    cleanup,
    retry,
    connected,
    active,
    loading,
    reconnectEnabled,
  } = useWebSocket({
    ...params,
    binaryType: "arraybuffer",
    onMessage: handleOnMessage,
    onClose: handleOnClose,
  });

  return {
    ws,
    initWS,
    send,
    closeWS,
    cleanup,
    retry,
    connected,
    active,
    loading,
    reconnectEnabled,
    handleImageOnLoad,
    imgRef,
    imgInitted,
    imgLoading,
  };
};
