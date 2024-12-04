import axios from "axios";
import { defineStore } from "pinia";
import { constrain } from "@/util/constrain";
import { downloadFile, removeFile } from "@/features/settings/api";
import { APIMediaType } from "@/features/settings/interface";
import { useMessagerStore } from "@/features/messager/store";
import { isNumber } from "@/util/guards";
import { cycleValue } from "@/util/cycleValue";

export interface FileDetail {
  track: string;
  duration: number;
  removable: boolean;
}

export enum MusicMode {
  LOOP = "loop",
  QUEUE = "queue",
  SINGLE = "single",
  LOOP_ONE = "loop_one",
}

export interface MusicPlayerInfo {
  track: string | null;
  position: number;
  is_playing: boolean;
  duration: number;
  mode: MusicMode;
}

export interface PlayMusicResponse {
  playing: boolean;
  track?: string;
  duration?: number;
  start?: number;
}

export interface State {
  data: FileDetail[];
  loading: boolean;
  volume?: number;
  timer?: NodeJS.Timeout;
  trackLoading?: boolean;
  player: MusicPlayerInfo;
}

const defaultState: State = {
  loading: false,
  data: [],
  player: {
    mode: MusicMode.LOOP,
    track: null,
    position: 0.0,
    is_playing: false,
    duration: 0.0,
  },
};

export const mediaType: APIMediaType = "music";

export const useStore = defineStore("music", {
  state: () => ({ ...defaultState }),
  actions: {
    async fetchData() {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        const response = await axios.get<{
          volume: number;
          files: FileDetail[];
        }>(`/api/music`);
        const respData = response.data;
        this.data = respData.files;
        this.volume = respData.volume;
      } catch (error) {
        messager.handleError(error, `Error fetching ${mediaType}`);
      } finally {
        this.loading = false;
      }
    },

    async togglePlaying() {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        await axios.post("/api/music/toggle-play");
      } catch (error) {
        messager.handleError(error, `Error toggling music playing`);
      } finally {
        this.loading = false;
      }
    },

    async stopPlaying() {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        await axios.post("/api/music/stop");
      } catch (error) {
        messager.handleError(error, `Error stopping music`);
      } finally {
        this.loading = false;
      }
    },

    async nextTrack() {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        await axios.post("/api/music/next-track");
      } catch (error) {
        messager.handleError(error, `Error switching to next track`);
      } finally {
        this.loading = false;
      }
    },

    async prevTrack() {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        await axios.post("/api/music/prev-track");
      } catch (error) {
        messager.handleError(error, `Error switching to previous track`);
      } finally {
        this.loading = false;
      }
    },

    async playTrack(track: string) {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        await axios.post("/api/music/track", { track });
      } catch (error) {
        messager.handleError(error, `Error seeking music`);
      } finally {
        this.loading = false;
      }
    },
    async updatePosition(position: number) {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        await axios.post("/api/music/position", { position });
      } catch (error) {
        messager.handleError(error, `Error seeking music`);
      } finally {
        this.loading = false;
      }
    },

    async updateMode(mode: MusicMode) {
      const messager = useMessagerStore();

      try {
        this.loading = true;
        await axios.post("/api/music/mode", { mode });
      } catch (error) {
        messager.handleError(error, `Error updating player mode`);
      } finally {
        this.loading = false;
      }
    },

    async cycleMode(direction: number) {
      this.player.mode = cycleValue(
        this.player.mode,
        Object.values(MusicMode),
        direction,
      );

      await this.updateMode(this.player.mode);
    },

    async nextMode() {
      await this.cycleMode(1);
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
        const response = await axios.post("/api/audio/volume", { volume });
        this.volume = response.data.volume;
      } catch (error) {
        messager.handleError(error);
      }
    },
    async getVolume() {
      const messager = useMessagerStore();
      try {
        const response = await axios.get<{ volume: number }>(
          "/api/audio/volume",
        );
        this.volume = response.data.volume;
        return this.volume;
      } catch (error) {
        messager.handleError(error);
      }
    },
    async updateMusicOrder(tracks: string[]) {
      const messager = useMessagerStore();
      try {
        this.loading = true;
        await axios.post("/api/music/order", tracks);
      } catch (error) {
        messager.handleError(error);
      } finally {
        this.loading = false;
      }
    },
  },
});
