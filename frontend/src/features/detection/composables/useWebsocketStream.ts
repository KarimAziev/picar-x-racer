import { ref, Ref } from "vue";
import { useWebSocket, WebSocketOptions } from "@/composables/useWebsocket";
import { useDetectionStore } from "@/features/detection";
import { useFPSStore } from "@/features/settings/stores";

export interface WebsocketStreamParams extends WebSocketOptions {
  imgRef: Ref<HTMLImageElement | undefined>;
}

const extractFrameWithMetadata = (data: ArrayBuffer) => {
  // Extract first 8 bytes for the timestamp (Double-precision float, 8 bytes)
  const dataView = new DataView(data);
  const timestamp = dataView.getFloat64(0, true);

  // Extract the next 8 bytes for the FPS (Double-precision float)
  const fps = dataView.getFloat64(8, true);

  // The rest of the data is the frame (starting from the 16th byte)
  const arrayBufferView = new Uint8Array(data, 16);
  const blob = new Blob([arrayBufferView], { type: "image/jpeg" });

  return { timestamp, fps, blob };
};

export const useWebsocketStream = (params: WebsocketStreamParams) => {
  const detectionStore = useDetectionStore();
  const fpsStore = useFPSStore();
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

    const { timestamp, blob, fps } = extractFrameWithMetadata(data);

    const imageUrl = urlCreator.createObjectURL(blob);

    detectionStore.setCurrentFrameTimestamp(timestamp);
    fpsStore.updateFPS(fps);

    if (params.imgRef.value) {
      params.imgRef.value.src = imageUrl;
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
    fpsStore.updateFPS(null);
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
    imgInitted,
    imgLoading,
  };
};
