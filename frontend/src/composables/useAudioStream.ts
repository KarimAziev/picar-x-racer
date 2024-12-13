import { ref } from "vue";
import { useWebSocket } from "@/composables/useWebsocket";

const createAudioContext = () => {
  return new (window.AudioContext || (window as any).webkitAudioContext)();
};

export const useWebsocketAudio = (url: string = "ws/audio-stream") => {
  const audioContext = ref<AudioContext | null>(null);
  const audioQueue = ref<Float32Array[]>([]);
  const isPlaying = ref(false);

  const handleOnMessage = (data: ArrayBuffer) => {
    const audioData = new Int16Array(data);

    const audioBuffer = new Float32Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      audioBuffer[i] = audioData[i] / 32768;
    }

    audioQueue.value.push(audioBuffer);

    if (!isPlaying.value) {
      processAudioQueue();
    }
  };

  const processAudioQueue = () => {
    if (audioQueue.value.length === 0) {
      isPlaying.value = false;
      return;
    }

    isPlaying.value = true;

    const audioBuffer = audioQueue.value.shift();
    if (!audioBuffer || !audioContext.value) {
      return;
    }

    const audioSource = audioContext.value.createBufferSource();
    const audioBufferData = audioContext.value.createBuffer(
      1,
      audioBuffer.length,
      audioContext.value.sampleRate,
    );

    audioBufferData.copyToChannel(audioBuffer, 0);
    audioSource.buffer = audioBufferData;

    audioSource.connect(audioContext.value.destination);
    audioSource.onended = processAudioQueue;
    audioSource.start();
  };

  const { ws, initWS, send, closeWS, cleanup, connected, active, loading } =
    useWebSocket({
      url,
      binaryType: "arraybuffer",
      onMessage: handleOnMessage,
      onClose: async () => {
        if (audioContext.value) {
          await audioContext.value.close();
          audioContext.value = null;
        }
      },
    });

  const startAudio = async () => {
    if (!audioContext.value || audioContext.value.state === "closed") {
      audioContext.value = createAudioContext();
    }

    if (audioContext.value.state === "suspended") {
      await audioContext.value.resume();
    }
    initWS();
  };

  const stopAudio = async () => {
    closeWS();
    audioQueue.value.length = 0;
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
