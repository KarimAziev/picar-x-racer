import { ref, Ref } from "vue";
import { useWebSocket, WebSocketOptions } from "@/composables/useWebsocket";
import { useDetectionStore } from "@/features/detection";
import { useStore as useFPSStore } from "@/features/settings/stores/fps";

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

  return { timestamp, serverFps: fps, blob };
};

export const useWebsocketStream = (params: WebsocketStreamParams) => {
  const detectionStore = useDetectionStore();
  const fpsStore = useFPSStore();
  const imgInitted = ref(false);
  const imgLoading = ref(true);
  const currentImageBlobUrl = ref<string>();

  let lastPerf: number = 0;
  let lastFPS: number = 0;

  const updateClientFPS = () => {
    const perf = performance.now();

    if (perf - lastPerf >= 1000) {
      const fps = lastFPS;
      lastPerf = perf;
      lastFPS = 0;
      fpsStore.updateFPS(fps);
    } else {
      lastFPS += 1;
    }
  };

  const handleImageOnLoad = () => {
    if (imgLoading.value) {
      imgLoading.value = false;
    }
    if (!imgInitted.value) {
      imgInitted.value = true;
    }
  };

  const handleOnMessage = (data: MessageEvent["data"]) => {
    updateClientFPS();
    if (params.onMessage) {
      params.onMessage(data);
    }

    const urlCreator = window.URL || window.webkitURL;
    if (currentImageBlobUrl.value) {
      urlCreator.revokeObjectURL(currentImageBlobUrl.value);
      currentImageBlobUrl.value = undefined;
    }

    const { timestamp, serverFps, blob } = extractFrameWithMetadata(data);
    const imageUrl = urlCreator.createObjectURL(blob);

    detectionStore.setCurrentFrameTimestamp(timestamp);
    fpsStore.updateServerFPS(serverFps);

    if (params.imgRef.value) {
      params.imgRef.value.onload = handleImageOnLoad;
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
    const urlCreator = window.URL || window.webkitURL;
    if (currentImageBlobUrl.value) {
      urlCreator.revokeObjectURL(currentImageBlobUrl.value);
      currentImageBlobUrl.value = undefined;
    }
    imgLoading.value = true;
    fpsStore.updateFPS(null);
    lastPerf = 0;
    lastFPS = 0;
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
