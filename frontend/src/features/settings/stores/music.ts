import axios from "axios";
import { defineStore } from "pinia";
import { constrain } from "@/util/constrain";
import { downloadFile, removeFile } from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";
import { useMessagerStore } from "@/features/messager/store";
import { isNumber } from "@/util/guards";
import { cycleValue } from "@/util/cycleValue";

export interface PlayMusicResponse {
  playing: boolean;
  track?: string;
  duration?: number;
  start?: number;
}

export interface State {
  data: string[];
  loading: boolean;
  defaultData: [];
  volume?: number;
  playing?: boolean;
  duration?: number;
  track: string | null;
  start: number;
  timer?: NodeJS.Timeout;
  trackLoading?: boolean;
}

const defaultState: State = {
  loading: false,
  data: [],
  defaultData: [],
  track: null,
  trackLoading: false,
  start: 0.0,
};

export const mediaType: APIMediaType = "music";

export const useStore = defineStore("music", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get(`/api/list_files/${mediaType}`);
        this.data = response.data.files;
      } catch (error) {
        messager.handleError(error, `Error fetching ${mediaType}`);
      } finally {
        this.loading = false;
      }
    },

    async fetchDefaultData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get(`/api/list_files/default_music`);
        this.defaultData = response.data.files;
      } catch (error) {
        messager.handleError(error, `Error fetching ${mediaType}`);
      } finally {
        this.loading = false;
      }
    },

    async removeFile(file: string) {
      const messager = useMessagerStore();
      try {
        await removeFile(mediaType, file);
      } catch (error) {
        messager.handleError(error);
      }
    },
    async downloadFile(fileName: string) {
      const messager = useMessagerStore();
      try {
        await downloadFile(mediaType, fileName);
      } catch (error) {
        messager.handleError(error);
      }
    },

    async increaseVolume() {
      if (!isNumber(this.volume)) {
        await this.getVolume();
      }
      await this.setVolume(constrain(0, 100, (this.volume || 0) + 10));
    },

    async decreaseVolume() {
      if (!isNumber(this.volume)) {
        await this.getVolume();
      }
      await this.setVolume(constrain(0, 100, (this.volume || 100) - 10));
    },

    async setVolume(volume: number) {
      const messager = useMessagerStore();
      try {
        const response = await axios.post("/api/volume", { volume });
        this.volume = response.data.volume;
        messager.info(`Volume: ${this.volume}`);
      } catch (error) {
        messager.handleError(error);
      }
    },
    async getVolume() {
      const messager = useMessagerStore();
      try {
        const response = await axios.get<{ volume: number }>("/api/volume");
        this.volume = response.data.volume;
        messager.info(`Volume: ${this.volume}`);
        return this.volume;
      } catch (error) {
        messager.handleError(error);
      }
    },
    async cycleTrack(direction: number, force?: boolean, start?: number) {
      const songs = [...this.data, ...this.defaultData];
      if (!songs.length) {
        await this.fetchData();
      }

      const messager = useMessagerStore();
      const nextTrack = cycleValue(
        this.track,
        [...this.data, ...this.defaultData],
        direction,
      );

      if (nextTrack !== this.track) {
        await this.playMusic(nextTrack, force, start);
      } else {
        messager.info("No next track");
      }
    },
    async nextTrack() {
      if (this.timer) {
        clearInterval(this.timer);
      }
      this.playing = true;
      this.start = 0.0;
      await this.cycleTrack(1, true, 0.0);
    },
    async prevTrack() {
      if (this.timer) {
        clearInterval(this.timer);
      }
      this.playing = true;
      this.start = 0.0;
      await this.cycleTrack(-1, true, 0.0);
    },
    async pauseMusic() {
      this.playing = false;
      const start = this.start;
      const track = this.track;
      const duration = this.duration;
      await this.playMusic(null);
      this.start = start;
      this.duration = duration;
      this.track = track;
    },

    async stopMusic() {
      this.playing = false;
      const track = this.track;
      const duration = this.duration;
      await this.playMusic(null);
      this.start = 0.0;
      this.track = track;
      this.duration = duration;
    },
    async resumeMusic() {
      this.playing = true;
      await this.playMusic(this.track, true, this.start);
    },
    startTimer() {
      if (this.timer) {
        clearInterval(this.timer);
      }
      if (this.playing && isNumber(this.duration) && isNumber(this.start)) {
        this.timer = setInterval(() => {
          if (!this.playing || !this.duration || this.start >= this.duration) {
            clearTimeout(this.timer);
          } else {
            this.start = (this.start || 0.0) + 1.0;
          }
        }, 1000);
      }
    },
    async playMusic(track: string | null, force?: boolean, start?: number) {
      const messager = useMessagerStore();
      try {
        this.trackLoading = true;
        const response = await axios.post<PlayMusicResponse>(
          `/api/play-music`,
          { filename: track, start: start || 0.0, force: force || false },
        );
        const data = response.data;

        this.playing = data.playing;

        if (data.track) {
          this.track = data.track;
        }
        if (isNumber(data.duration)) {
          this.duration = data.duration;
        }

        if (isNumber(data.start)) {
          this.start = data.start;
        }

        this.startTimer();
        return data;
      } catch (error) {
        messager.handleError(error);
      } finally {
        this.trackLoading = false;
      }
    },

    async getCurrentStatus() {
      const messager = useMessagerStore();
      try {
        this.trackLoading = true;
        const response = await axios.get<PlayMusicResponse>(`/api/play-status`);
        const data = response.data;
        this.playing = data.playing;
        if (data.track) {
          this.track = data.track;
        }
        if (isNumber(data.duration)) {
          this.duration = data.duration;
        }

        if (isNumber(data.start)) {
          this.start = data.start;
        }
        this.startTimer();
      } catch (error) {
        messager.handleError(error, `Error fetching music status`);
      } finally {
        this.trackLoading = false;
      }
    },
  },
});
