from typing import Any, Dict, Optional, Union

from app.util.logger import Logger
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class ConnectionService:
    """
    A service that manages WebSocket connections, allowing for real-time communication with connected clients.
    This service provides functionality to connect, disconnect, and broadcast messages to multiple WebSocket connections.
    """

    def __init__(self, app_name: Optional[str] = None):
        """
        Initializes the ConnectionService instance.

        Args:
            app_name (Optional[str]): The name of the application for scoping the logger, if needed. Defaults to None.
        """
        self.logger = Logger(name=__name__, app_name=app_name)
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Establishes a WebSocket connection by accepting it and adding it to the active connections list.

        Args:
            websocket (WebSocket): The WebSocket connection object representing the client's connection.

        Side Effects:
            Adds the WebSocket to the list of active connections.
            Logs the total number of connected clients after the connection is established.
        """
        await websocket.accept()

        self.active_connections.append(websocket)
        self.logger.info(f"Connected {len(self.active_connections)} clients")

    async def disconnect(self, websocket: WebSocket):
        """
        Handles the disconnection of a WebSocket connection. Removes the connection from the active
        connections list and attempts to close the WebSocket gracefully, if still connected.

        Args:
            websocket (WebSocket): The WebSocket connection object representing the client's connection.

        Side Effects:
            Removes the WebSocket from the active connections list.
            Closes the WebSocket connection, if it is still connected.
            Logs the updated total number of clients after disconnection.
        """
        self.remove(websocket)
        self.logger.info(
            f"Removing connection, total clients: {len(self.active_connections)}"
        )

        if websocket.application_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except RuntimeError as ex:
                self.logger.error(
                    f"Failed to close weboscket due to RuntimeError: {ex}"
                )

    def remove(self, websocket: WebSocket):
        """
        Removes a WebSocket connection from the list of active connections.

        Args:
            websocket (WebSocket): The WebSocket connection object to be removed.

        Side Effects:
            If the WebSocket is in the list of active connections, it will be removed.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data: Any, mode: str = "text"):
        """
        Broadcasts a JSON-serializable payload to all connected WebSocket clients.
        Automatically handles disconnected clients during the broadcast.

        Args:
            data (Any): The JSON-serializable data to send to all clients.
            mode (str): The mode of transmission (default is "text"). Defaults to "text".

        Side Effects:
            Sends JSON data to all currently connected clients.
            Removes clients that disconnect during the broadcast.
        """
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data, mode)
            except WebSocketDisconnect:
                disconnected_clients.append(connection)

        for connection in disconnected_clients:
            await self.disconnect(connection)

    async def broadcast_bytes(self, data: Any):
        """
        Broadcasts a binary payload to all connected WebSocket clients.
        Automatically handles disconnected clients during the broadcast.

        Args:
            data (Any): The binary data to send to all clients.

        Side Effects:
            Sends binary data to all currently connected clients.
            Removes clients that disconnect during the broadcast.
        """
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_bytes(data)
            except WebSocketDisconnect:
                disconnected_clients.append(connection)

        for connection in disconnected_clients:
            await self.disconnect(connection)

    async def broadcast(self, data: str):
        """
        Broadcasts a text message to all connected WebSocket clients.
        Automatically handles disconnected clients during the broadcast.

        Args:
            data (str): The plain-text message to send to all clients.

        Side Effects:
            Sends text messages to all currently connected clients.
            Removes clients that disconnect during the broadcast.
        """
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except WebSocketDisconnect:
                disconnected_clients.append(connection)

        for connection in disconnected_clients:
            await self.disconnect(connection)

    async def info(self, msg: Union[str, Dict[str, Any]]):
        await self.broadcast_json({"type": "info", "payload": msg})

    async def error(self, msg: Union[str, Dict[str, Any]]):
        await self.broadcast_json({"type": "error", "payload": msg})
