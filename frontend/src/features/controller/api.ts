import axios from "axios";

export const playMusic = (filename: string) =>
  axios.post(`/api/play-music`, { filename });

export const playSound = (filename: string) =>
  axios.post(`/api/play-sound`, { filename });

export const playTTS = (text: string, lang?: string) =>
  axios.post(`/api/play-tts`, { text, lang });

export const takePhoto = () => axios.get(`/api/take-photo`);
