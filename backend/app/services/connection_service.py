from typing import Optional

from app.services.client_notifier import ClientNotifier
from app.util.logger import Logger
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionService:
    """Handles WebSocket connections and broadcasts messages to connected clients."""

    def __init__(self, notifier: "ClientNotifier", app_name: Optional[str] = None):
        """
        Initialize the ConnectionService with a notifier.

        Args:
            notifier (ClientNotifier): The service with async `handle_notify_client` method.
        """
        self.logger = Logger(name=__name__, app_name=app_name)
        self.notifier = notifier
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Accept a WebSocket connection, add it to active connections, and notify the client.

        Args:
            websocket (WebSocket): The WebSocket connection instance.
        """
        await websocket.accept()

        self.active_connections.append(websocket)
        self.logger.info(f"Connected {len(self.active_connections)} clients")
        await self.notifier.handle_notify_client(websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from the list of active connections.

        Args:
            websocket (WebSocket): The WebSocket connection instance to remove.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.logger.info(
            f"Removing connection, total clients: {len(self.active_connections)}"
        )

    async def broadcast(self):
        """
        Broadcast messages to all connected clients and handle disconnections.
        """
        disconnected_clients = []

        for connection in self.active_connections:
            try:
                await self.notifier.handle_notify_client(connection)
            except WebSocketDisconnect:
                disconnected_clients.append(connection)

        for connection in disconnected_clients:
            self.disconnect(connection)
