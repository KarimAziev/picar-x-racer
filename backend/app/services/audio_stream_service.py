import asyncio
import threading
from queue import Empty, Queue
from typing import AsyncGenerator, Optional

import sounddevice as sd
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from fastapi import WebSocket, WebSocketDisconnect


class AudioStreamService(metaclass=SingletonMeta):
    """
    Service to capture audio in real time using the microphone.
    """

    def __init__(self):
        self.logger = Logger(name=__name__)
        self.sample_rate = 44100  # Audio sampling rate in Hz
        self.channels = 1  # Mono audio
        self.block_size = 1024  # Number of audio samples per block
        self.running = False  # Flag to indicate whether audio capture is running
        self.audio_thread: Optional[threading.Thread] = None
        self.audio_queue = Queue(maxsize=100)  # Buffer to store audio chunks
        self.audio_stream = None  # Sounddevice InputStream object
        self.active_clients = 0

    def _capture_worker(self):
        """
        Background worker to capture audio in real time and push it to the queue.
        """
        try:
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.block_size,
                dtype="int16",
                callback=lambda indata, frames, time, status: self.audio_queue.put_nowait(
                    indata.copy()
                ),
            )
            self.audio_stream.start()
            self.logger.info("Audio capture started.")

            while self.running:
                sd.sleep(100)  # Keep stream alive
        except Exception as e:
            self.logger.log_exception("Error in audio capture worker", e)

        finally:
            if self.audio_stream:
                self.audio_stream.stop()
                self.audio_stream.close()
            self.audio_stream = None
            self.logger.info("Audio capture stopped.")

    def start_audio_capture(self):
        """
        Start audio capture in a background thread.
        """
        if self.running:
            self.logger.info("Audio capture is already running.")
            return
        self.running = True
        self.audio_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.audio_thread.start()

    def stop_audio_capture(self):
        """
        Stop the audio capture process and clean up resources.
        """
        if not self.running:
            self.logger.info("Audio capture is not running.")
            return
        self.running = False
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join()

    async def generate_audio_chunks(self) -> AsyncGenerator[bytes, None]:
        """
        Async generator to yield audio chunks from the queue in real time.
        """
        if not self.running:
            await asyncio.to_thread(self.start_audio_capture)

        while self.running:
            try:
                chunk = await asyncio.to_thread(self.audio_queue.get, timeout=1)
                yield chunk.tobytes()
            except Empty:
                self.logger.info("No audio chunks available, stopping generator.")
                break

    async def audio_stream_to_ws(self, websocket: WebSocket):
        """
        Handles an incoming WebSocket connection for audio streaming.

        This method is called for each new WebSocket connection.
        """
        self.logger.info(f"WebSocket connection established: {websocket.client}")
        self.active_clients += 1

        try:
            await websocket.accept()
            async for audio_chunk in self.generate_audio_chunks():
                await websocket.send_bytes(audio_chunk)
        except WebSocketDisconnect:
            self.logger.info(f"WebSocket Disconnected {websocket.client}")
        except asyncio.CancelledError:
            self.logger.info("Gracefully shutting down WebSocket stream connection")
        except Exception:
            self.logger.log_exception("An error occurred in video stream")
        finally:
            self.active_clients -= 1
            if self.active_clients == 0:
                self.logger.info(
                    f"WebSocket connection closed: {websocket.client}, Active clients: {self.active_clients}"
                )
                await asyncio.to_thread(self.stop_audio_capture)
            else:
                self.logger.info(
                    f"WebSocket connection closed: {websocket.client}, Active clients: {self.active_clients}"
                )
