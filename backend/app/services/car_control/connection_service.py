from typing import TYPE_CHECKING

from app.util.logger import Logger
from fastapi import WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from app.services.car_control.car_service import CarService


class ConnectionService:
    """Handles WebSocket connections and broadcasts messages to connected clients."""

    def __init__(self, car_manager: "CarService"):
        """
        Initialize the ConnectionService with a car manager.

        Args:
            car_manager (CarService): The car manager service responsible for handling car operations.
        """
        self.logger = Logger(name=__name__, app_name="px-control")
        self.car_manager = car_manager
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Accept a WebSocket connection, add it to active connections, and notify the client.

        Args:
            websocket (WebSocket): The WebSocket connection instance.
        """
        self.logger.debug("Connecting new client")
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.debug(f"Connected {len(self.active_connections)} clients")
        await self.car_manager.handle_notify_client(websocket)
        self.logger.debug("Notifying new client")

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from the list of active connections.

        Args:
            websocket (WebSocket): The WebSocket connection instance to remove.
        """
        self.active_connections.remove(websocket)

    async def broadcast(self):
        """
        Broadcast messages to all connected clients and handle disconnections.
        """
        disconnected_clients = []

        for connection in self.active_connections:
            try:
                await self.car_manager.handle_notify_client(connection)
            except WebSocketDisconnect:
                disconnected_clients.append(connection)

        for connection in disconnected_clients:
            self.disconnect(connection)
