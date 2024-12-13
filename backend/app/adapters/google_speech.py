"""
This module provides functionality for text-to-speech synthesis using the Google Translate TTS API.

It is a refactored version of the original `google_speech` library but replaces
the use of `sox` with `pygame` for audio playback.

While the core functionality remains the same, the sound effects are no longer supported.
"""

import argparse
import collections
import io
import os
import re
import string
import sys
import threading
import unicodedata
import urllib.parse
from typing import List

import appdirs
import requests
import web_cache
from app.util.logger import Logger

original_stdout = sys.stdout
try:
    sys.stdout = open(os.devnull, 'w')
    import pygame
finally:
    sys.stdout.close()
    sys.stdout = original_stdout


logger = Logger(__name__)

SUPPORTED_LANGUAGES = (
    "af",
    "ar",
    "bn",
    "bs",
    "ca",
    "cs",
    "cy",
    "da",
    "de",
    "el",
    "en",
    "en-au",
    "en-ca",
    "en-gb",
    "en-gh",
    "en-ie",
    "en-in",
    "en-ng",
    "en-nz",
    "en-ph",
    "en-tz",
    "en-uk",
    "en-us",
    "en-za",
    "eo",
    "es",
    "es-es",
    "es-us",
    "et",
    "fi",
    "fr",
    "fr-ca",
    "fr-fr",
    "hi",
    "hr",
    "hu",
    "hy",
    "id",
    "is",
    "it",
    "ja",
    "jw",
    "km",
    "ko",
    "la",
    "lv",
    "mk",
    "ml",
    "mr",
    "my",
    "ne",
    "nl",
    "no",
    "pl",
    "pt",
    "pt-br",
    "pt-pt",
    "ro",
    "ru",
    "si",
    "sk",
    "sq",
    "sr",
    "su",
    "sv",
    "sw",
    "ta",
    "te",
    "th",
    "tl",
    "tr",
    "uk",
    "vi",
    "zh-cn",
    "zh-tw",
)

PRELOADER_THREAD_COUNT = 1


class PreloaderThread(threading.Thread):
    """Thread to pre load (download and store in cache) audio data of a segment."""

    def __init__(self, segments: List['SpeechSegment'] = [], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.segments: List[SpeechSegment] = segments

    def run(self):
        """See threading.Thread.run."""
        try:
            for segment in self.segments:
                acquired = segment.preload_mutex.acquire(blocking=False)
                if acquired:
                    try:
                        if not segment.is_in_cache():
                            segment.pre_load()
                    finally:
                        segment.preload_mutex.release()
        except Exception as e:
            logger.error("%s: %s" % (e.__class__.__qualname__, e))


class Speech:
    """Text to be read."""

    CLEAN_MULTIPLE_SPACES_REGEX = re.compile(r"\s{2,}")
    MAX_SEGMENT_SIZE = 200

    def __init__(self, text, lang):
        self.text = self.clean_spaces(text)
        self.lang = lang

    def __iter__(self):
        """Get an iterator over speech segments."""
        return self.__next__()

    def __next__(self):
        """Get a speech segment, splitting text by taking into account spaces, punctuation, and maximum segment size."""
        if self.text == "-":
            if sys.stdin.isatty():
                logger.error("Stdin is not a pipe")
                return
            while True:
                new_line = sys.stdin.readline()
                if not new_line:
                    return
                segments = __class__.split_text(new_line)
                for segment_num, segment in enumerate(segments):
                    yield SpeechSegment(segment, self.lang, segment_num, len(segments))

        else:
            segments = __class__.split_text(self.text)
            for segment_num, segment in enumerate(segments):
                yield SpeechSegment(segment, self.lang, segment_num, len(segments))

    @staticmethod
    def find_last_char_index_matching(text, func):
        """Return index of last character in string for which func(char) evaluates to True."""
        for i in range(len(text) - 1, -1, -1):
            if func(text[i]):
                return i

    @staticmethod
    def split_text(text):
        """Split text into sub segments of size not bigger than MAX_SEGMENT_SIZE."""
        segments = []
        remaining_text = __class__.clean_spaces(text)

        while len(remaining_text) > __class__.MAX_SEGMENT_SIZE:
            cur_text = remaining_text[: __class__.MAX_SEGMENT_SIZE]

            # try to split at punctuation
            split_idx = __class__.find_last_char_index_matching(
                cur_text,
                # https://en.wikipedia.org/wiki/Unicode_character_property#General_Category
                lambda x: unicodedata.category(x) in ("Ps", "Pe", "Pi", "Pf", "Po"),
            )
            if split_idx is None:
                # try to split at whitespace
                split_idx = __class__.find_last_char_index_matching(
                    cur_text, lambda x: unicodedata.category(x).startswith("Z")
                )
            if split_idx is None:
                # try to split at anything not a letter or number
                split_idx = __class__.find_last_char_index_matching(
                    cur_text, lambda x: not (unicodedata.category(x)[0] in ("L", "N"))
                )
            if split_idx is None:
                # split at the last char
                split_idx = __class__.MAX_SEGMENT_SIZE - 1

            new_segment = cur_text[: split_idx + 1].rstrip()
            segments.append(new_segment)
            remaining_text = remaining_text[split_idx + 1 :].lstrip(
                string.whitespace + string.punctuation
            )

        if remaining_text:
            segments.append(remaining_text)

        return segments

    @staticmethod
    def clean_spaces(dirty_string):
        """Remove consecutive spaces from a string."""
        return __class__.CLEAN_MULTIPLE_SPACES_REGEX.sub(
            " ", dirty_string.replace("\n", " ").replace("\t", " ").strip()
        )

    def play(self):
        """Play a speech."""

        # build the segments
        preloader_threads = []
        if self.text != "-":
            segments = list(self)
            # start preloader thread(s)
            preloader_threads = [
                PreloaderThread(name="PreloaderThread-%u" % (i))
                for i in range(PRELOADER_THREAD_COUNT)
            ]
            for preloader_thread in preloader_threads:
                preloader_thread.segments = segments
                preloader_thread.start()
        else:
            segments = iter(self)

        # play segments
        for segment in segments:
            segment.play()

        if self.text != "-":
            # destroy preloader threads
            for preloader_thread in preloader_threads:
                preloader_thread.join()

    def save(self, path):
        """Save audio data to an MP3 file."""
        with open(path, "wb") as f:
            self.savef(f)

    def savef(self, file):
        """Write audio data into a file object."""
        for segment in self:
            file.write(segment.get_audio_data())


class SpeechSegment:
    """Text segment to be read."""

    BASE_URL = "https://translate.google.com/translate_tts"
    session = requests.Session()
    cache: "web_cache.WebCache"

    def __init__(self, text, lang, segment_num, segment_count=None):
        self.text = text
        self.lang = lang
        self.segment_num = segment_num
        self.segment_count = segment_count
        self.preload_mutex = threading.Lock()
        if not hasattr(__class__, "cache"):
            db_filepath = os.path.join(
                appdirs.user_cache_dir(appname="google_speech", appauthor=False),
                "google_speech-cache.sqlite",
            )
            os.makedirs(os.path.dirname(db_filepath), exist_ok=True)
            cache_name = "sound_data"
            __class__.cache = web_cache.ThreadedWebCache(
                db_filepath,
                cache_name,
                expiration=60 * 60 * 24 * 365,  # 1 year
                caching_strategy=web_cache.CachingStrategy.LRU,
            )  # type: ignore
            logger.debug(
                "Total size of file '%s': %s"
                % (db_filepath, __class__.cache.getDatabaseFileSize())
            )
            purged_count = __class__.cache.purge()
            logger.debug(
                "%u obsolete entries have been removed from cache '%s'"
                % (purged_count, cache_name)
            )
            row_count = len(__class__.cache)
            logger.debug("Cache '%s' contains %u entries" % (cache_name, row_count))

    def __str__(self):
        return self.text

    def is_in_cache(self):
        """Return True if audio data for this segment is present in cache, False otherwise."""
        url = self.build_url()
        return url in __class__.cache

    def pre_load(self):
        """Store audio data in cache for fast playback."""
        logger.debug("Preloading segment '%s'" % (self))
        real_url = self.build_url()
        cache_url = self.build_url()
        audio_data = self.download(real_url)
        assert audio_data
        __class__.cache[cache_url] = audio_data

    def get_audio_data(self):
        """Fetch the audio data."""
        with self.preload_mutex:
            cache_url = self.build_url()
            if cache_url in __class__.cache:
                logger.debug("Got data for URL '%s' from cache" % (cache_url))
                audio_data = __class__.cache[cache_url]
                assert audio_data
            else:
                real_url = self.build_url()
                audio_data = self.download(real_url)
                assert audio_data
                __class__.cache[cache_url] = audio_data
        return audio_data

    def play(self):
        """Play the segment using Pygame."""
        audio_data = self.get_audio_data()
        logger.info("Playing speech segment (%s): '%s'" % (self.lang, self))

        pygame.mixer.init()

        try:
            audio_file = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_file, "mp3")

            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

        finally:
            pygame.mixer.quit()

    def build_url(self):
        """
        Construct the URL to get the sound from the Google API.
        """
        params = collections.OrderedDict()
        params["client"] = "tw-ob"
        params["ie"] = "UTF-8"
        params["idx"] = str(self.segment_num)
        if self.segment_count is not None:
            params["total"] = str(self.segment_count)
        params["textlen"] = str(len(self.text))
        params["tl"] = self.lang
        lower_text = self.text.lower()
        params["q"] = lower_text
        return "%s?%s" % (__class__.BASE_URL, urllib.parse.urlencode(params))

    def download(self, url):
        """Download a sound file."""
        logger.debug("Downloading '%s'..." % (url))
        response = __class__.session.get(
            url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3.1
        )
        response.raise_for_status()
        return response.content


def cl_main():
    """Command line entry point for google_speech."""
    arg_parser = argparse.ArgumentParser(
        description="Google Speech",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    arg_parser.add_argument("speech", help="Text to play")
    arg_parser.add_argument(
        "-l",
        "--lang",
        choices=SUPPORTED_LANGUAGES,
        default="en",
        dest="lang",
        help="Language",
    )
    arg_parser.add_argument(
        "-o",
        "--output",
        default=None,
        dest="output",
        help="Outputs audio data to this file instead of playing it",
    )
    args = arg_parser.parse_args()

    speech = Speech(args.speech, args.lang)
    if args.output:
        speech.save(args.output)
    else:
        speech.play()


if __name__ == "__main__":
    cl_main()
