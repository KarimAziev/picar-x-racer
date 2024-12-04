import axios from "axios";

export const playTTS = (text: string, lang?: string) =>
  axios.post(`/api/tts/speak`, { text, lang });

export const takePhoto = () => axios.get(`/api/camera/capture-photo`);
