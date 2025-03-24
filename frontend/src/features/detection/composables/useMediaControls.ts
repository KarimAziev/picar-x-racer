import {
  isObject,
  defaultDocument,
  createEventHook,
  toValue,
  toRef,
  tryOnScopeDispose,
  useEventListener,
  useMediaControls as origUseMediaControls,
  watchIgnorable,
  UseMediaTextTrack,
  UseMediaControlsReturn,
} from "@vueuse/core";
import { watch, watchEffect, ref } from "vue";

export type UseMediaParams = Parameters<typeof origUseMediaControls>;
export type UseMediaControlsTarget = UseMediaParams[0];
export type UseMediaControlsOptions = UseMediaParams[1];

function usingElRef(source: UseMediaControlsTarget, cb: (...args: any) => any) {
  if (toValue(source)) cb(toValue(source));
}
function timeRangeToArray(timeRanges: TimeRanges) {
  let ranges = [];
  for (let i = 0; i < timeRanges.length; ++i)
    ranges = [...ranges, [timeRanges.start(i), timeRanges.end(i)]];
  return ranges;
}

const tracksToArray = (tracks: UseMediaTextTrack[]) =>
  Array.from(tracks).map(
    (
      {
        label,
        kind,
        language,
        mode,
        activeCues,
        cues,
        inBandMetadataTrackDispatchType,
      },
      id,
    ) => ({
      id,
      label,
      kind,
      language,
      mode,
      activeCues,
      cues,
      inBandMetadataTrackDispatchType,
    }),
  );

const defaultOptions: UseMediaControlsOptions = {
  src: "",
  tracks: [],
};

// Custom version of useMediaControls that loads track only if preload attribute isn’t "none"
export function useMediaControls(
  target: UseMediaControlsTarget,
  options: UseMediaControlsOptions = {},
): UseMediaControlsReturn {
  target = toRef(target);
  options = {
    ...defaultOptions,
    ...options,
  };

  const { document = defaultDocument } = options;
  const currentTime = ref(0);
  const duration = ref(0);
  const seeking = ref(false);
  const volume = ref(1);
  const waiting = ref(false);
  const muted = ref(false);
  const ended = ref(false);
  const playing = ref(false);
  const rate = ref(1);
  const stalled = ref(false);
  const buffered = ref([]);
  const tracks = ref<UseMediaTextTrack[]>([]);
  const selectedTrack = ref(-1);
  const isPictureInPicture = ref(false);
  const supportsPictureInPicture =
    document && "pictureInPictureEnabled" in document;
  const sourceErrorEvent = createEventHook();
  const playbackErrorEvent = createEventHook();

  const disableTrack = (track?: number | { id: number }) => {
    usingElRef(target, (el) => {
      if (track) {
        const id = typeof track === "number" ? track : track.id;
        el.textTracks[id].mode = "disabled";
      } else {
        for (let i = 0; i < el.textTracks.length; ++i)
          el.textTracks[i].mode = "disabled";
      }
      selectedTrack.value = -1;
    });
  };

  const enableTrack = (
    track?: number | { id: number },
    disableTracks = true,
  ) => {
    usingElRef(target, (el) => {
      const id = typeof track === "number" ? track : track.id;
      if (disableTracks) disableTrack();
      el.textTracks[id].mode = "showing";
      selectedTrack.value = id;
    });
  };

  const togglePictureInPicture = () => {
    return new Promise((resolve, reject) => {
      usingElRef(target, async (el) => {
        if (supportsPictureInPicture) {
          if (!isPictureInPicture.value) {
            el.requestPictureInPicture().then(resolve).catch(reject);
          } else {
            document.exitPictureInPicture().then(resolve).catch(reject);
          }
        }
      });
    });
  };

  watchEffect(() => {
    if (!document) return;
    const el = toValue(target);
    if (!el) return;
    const src = toValue(options.src);
    let sources = [];
    if (!src) return;
    if (typeof src === "string") sources = [{ src }];
    else if (Array.isArray(src)) sources = src;
    else if (isObject(src)) sources = [src];

    el.querySelectorAll("source").forEach((e) => {
      e.removeEventListener("error", sourceErrorEvent.trigger);
      e.remove();
    });

    sources.forEach(({ src: srcValue, type, media }) => {
      const source = document.createElement("source");
      source.setAttribute("src", srcValue);
      source.setAttribute("type", type || "");
      source.setAttribute("media", media || "");
      source.addEventListener("error", sourceErrorEvent.trigger);
      el.appendChild(source);
    });

    // Only auto-load if preload isn’t "none"
    if (el.getAttribute("preload") !== "none") {
      el.load();
    }
  });

  tryOnScopeDispose(() => {
    const el = toValue(target);
    if (!el) return;
    el.querySelectorAll("source").forEach((e) =>
      e.removeEventListener("error", sourceErrorEvent.trigger),
    );
  });

  watch([target, volume], () => {
    const el = toValue(target);
    if (!el) return;
    el.volume = volume.value;
  });

  watch([target, muted], () => {
    const el = toValue(target);
    if (!el) return;
    el.muted = muted.value;
  });

  watch([target, rate], () => {
    const el = toValue(target);
    if (!el) return;
    el.playbackRate = rate.value;
  });

  watchEffect(() => {
    if (!document) return;
    const textTracks = toValue(options.tracks);
    const el = toValue(target);
    if (!textTracks || !textTracks.length || !el) return;
    el.querySelectorAll("track").forEach((e) => e.remove());
    textTracks.forEach(
      ({ default: isDefault, kind, label, src, srcLang }, i) => {
        const track = document.createElement("track");
        track.default = isDefault || false;
        track.kind = kind;
        track.label = label;
        track.src = src;
        track.srclang = srcLang;
        if (track.default) selectedTrack.value = i;
        el.appendChild(track);
      },
    );
  });

  const { ignoreUpdates: ignoreCurrentTimeUpdates } = watchIgnorable(
    currentTime,
    (time) => {
      const el = toValue(target);
      if (!el) return;
      el.currentTime = time;
    },
  );

  // When playing changes, if preload="none" and the media has not loaded yet (readyState=0),
  // explicitly call load() before attempting to play.
  const { ignoreUpdates: ignorePlayingUpdates } = watchIgnorable(
    playing,
    (isPlaying) => {
      const el = toValue(target);
      if (!el) return;
      if (isPlaying) {
        if (el.getAttribute("preload") === "none" && el.readyState === 0) {
          el.load();
        }
        el.play().catch((e) => {
          playbackErrorEvent.trigger(e);
          throw e;
        });
      } else {
        el.pause();
      }
    },
  );

  useEventListener(target, "timeupdate", () =>
    ignoreCurrentTimeUpdates(() => {
      currentTime.value = toValue(target).currentTime;
    }),
  );

  useEventListener(target, "durationchange", () => {
    duration.value = toValue(target).duration;
  });

  useEventListener(target, "progress", () => {
    buffered.value = timeRangeToArray(toValue(target).buffered);
  });

  useEventListener(target, "seeking", () => {
    seeking.value = true;
  });

  useEventListener(target, "seeked", () => {
    seeking.value = false;
  });

  useEventListener(target, ["waiting", "loadstart"], () => {
    waiting.value = true;
    ignorePlayingUpdates(() => (playing.value = false));
  });

  useEventListener(target, "loadeddata", () => {
    waiting.value = false;
  });

  useEventListener(target, "playing", () => {
    waiting.value = false;
    ended.value = false;
    ignorePlayingUpdates(() => (playing.value = true));
  });

  useEventListener(target, "ratechange", () => {
    rate.value = toValue(target).playbackRate;
  });

  useEventListener(target, "stalled", () => {
    stalled.value = true;
  });

  useEventListener(target, "ended", () => {
    ended.value = true;
  });

  useEventListener(target, "pause", () =>
    ignorePlayingUpdates(() => (playing.value = false)),
  );
  useEventListener(target, "play", () =>
    ignorePlayingUpdates(() => (playing.value = true)),
  );
  useEventListener(target, "enterpictureinpicture", () => {
    isPictureInPicture.value = true;
  });
  useEventListener(target, "leavepictureinpicture", () => {
    isPictureInPicture.value = false;
  });
  useEventListener(target, "volumechange", () => {
    const el = toValue(target);
    if (!el) return;
    volume.value = el.volume;
    muted.value = el.muted;
  });

  const listeners = [];
  const stop = watch([target], () => {
    const el = toValue(target);
    if (!el) return;
    stop();
    listeners[0] = useEventListener(el.textTracks, "addtrack", () => {
      tracks.value = tracksToArray(
        el.textTracks as unknown as UseMediaTextTrack[],
      );
    });
    listeners[1] = useEventListener(el.textTracks, "removetrack", () => {
      tracks.value = tracksToArray(
        el.textTracks as unknown as UseMediaTextTrack[],
      );
    });
    listeners[2] = useEventListener(el.textTracks, "change", () => {
      tracks.value = tracksToArray(
        el.textTracks as unknown as UseMediaTextTrack[],
      );
    });
  });
  tryOnScopeDispose(() => listeners.forEach((listener) => listener()));

  return {
    currentTime,
    duration,
    waiting,
    seeking,
    ended,
    stalled,
    buffered,
    playing,
    rate,
    // Volume
    volume,
    muted,
    // Tracks
    tracks,
    selectedTrack,
    enableTrack,
    disableTrack,
    // Picture in Picture
    supportsPictureInPicture,
    togglePictureInPicture,
    isPictureInPicture,
    // Events
    onSourceError: sourceErrorEvent.on,
    onPlaybackError: playbackErrorEvent.on,
  };
}
