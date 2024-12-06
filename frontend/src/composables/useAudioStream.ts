import { ref } from "vue";
import { useWebSocket } from "@/composables/useWebsocket";

const createAudioContext = () => {
  return new (window.AudioContext || (window as any).webkitAudioContext)();
};

export const useWebsocketAudio = (url: string = "ws/audio-stream") => {
  const audioContext = createAudioContext();
  const audioQueue: Float32Array[] = [];
  const isPlaying = ref(false);

  const handleOnMessage = (data: ArrayBuffer) => {
    const audioData = new Int16Array(data);

    const audioBuffer = new Float32Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      audioBuffer[i] = audioData[i] / 32768;
    }

    audioQueue.push(audioBuffer);

    if (!isPlaying.value) {
      processAudioQueue();
    }
  };

  const processAudioQueue = () => {
    if (audioQueue.length === 0) {
      isPlaying.value = false;
      return;
    }

    isPlaying.value = true;

    const audioBuffer = audioQueue.shift();
    if (!audioBuffer) return;

    const audioSource = audioContext.createBufferSource();
    const audioBufferData = audioContext.createBuffer(
      1,
      audioBuffer.length,
      audioContext.sampleRate,
    );

    audioBufferData.copyToChannel(audioBuffer, 0);
    audioSource.buffer = audioBufferData;

    audioSource.connect(audioContext.destination);
    audioSource.onended = processAudioQueue;
    audioSource.start();
  };

  const { ws, initWS, send, closeWS, cleanup, connected, active, loading } =
    useWebSocket({
      url,
      binaryType: "arraybuffer",
      onMessage: handleOnMessage,
    });

  const startAudio = async () => {
    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }
    initWS();
  };

  const stopAudio = () => {
    closeWS();
    audioQueue.length = 0;
    isPlaying.value = false;
  };

  return {
    startAudio,
    stopAudio,
    cleanup,
    connected,
    active,
    loading,
    ws,
    send,
  };
};
