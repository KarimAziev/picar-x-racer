from abc import ABC, abstractmethod

from fastapi import WebSocket


class ClientNotifier(ABC):
    """
    Abstract base class for services that can notify clients. Any class inheriting
    from this must implement the 'handle_notify_client' method.
    """

    @abstractmethod
    async def handle_notify_client(self, websocket: WebSocket):
        """
        Must implement the method that handles notifications for clients over a WebSocket.

        Args:
            websocket (WebSocket): The WebSocket connection instance.
        """
        pass
