from typing import Any, Optional

from app.core.async_emitter import AsyncEventEmitter
from app.core.logger import Logger
from app.schemas.connection import ConnectionEvent
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class ConnectionService(AsyncEventEmitter):
    """
    A service that manages WebSocket connections, enabling real-time communication with connected clients.

    This class provides functionality to:
    - Establish and terminate WebSocket connections (`connect` and `disconnect`).
    - Broadcast data in various formats:
        - Text messages (`broadcast`)
        - JSON payloads (`broadcast_json`)
        - Binary data (`broadcast_bytes`)
    - Notify connected clients with utility messages (`info`, `warning`, `error`) for specific types of updates.
    - Emit events triggered by key connection state changes:
        - `first_connection_ever` (once per application lifecycle): Triggered when the first WebSocket connection is established in
          the application's lifecycle.
        - `first_active_connection` (repeated): Triggered each time the first client connects (i.e., when active connections transition from 0 to 1, but not from 2 to 1)."
        - `last_connection` (repeated): Triggered when the last active WebSocket connection is closed, leaving no
          clients connected.

    Example usage:
        - Listen for events:

        ```python
        connection_service = ConnectionService()

        @connection_service.on(ConnectionEvent.FIRST_CONNECTION_EVER.value)
        async def handle_first_connection():
            print("First ever connection occurred!")

        @connection_service.on(ConnectionEvent.LAST_CONNECTION.value)
        async def handle_last_connection():
            print("All clients disconnected!")
        ```
    """

    def __init__(self, app_name: Optional[str] = None, *args, **kwargs):
        """
        Initializes the ConnectionService instance.

        Args:
            app_name (Optional[str]): The name of the application for scoping the logger, if needed. Defaults to None.
        """
        super().__init__(*args, **kwargs)
        self.had_connections = False
        self._log = Logger(name=__name__, app_name=app_name)
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Establishes a WebSocket connection by accepting it and adding it to the active connections list.

        Emits:
            - `first_connection_ever` (only once): If this is the first WebSocket connection
              established since the application started.
            - `first_active_connection`: If this is the first active connection after all
              previous connections were closed.

        Args:
            websocket (WebSocket): The WebSocket connection object representing the client's connection.

        Side Effects:
            - Adds the WebSocket to the list of active connections.
            - Logs the total number of connected clients after the connection is established.
            - Emits relevant events based on connection state.

        Examples:
            ```python
            service = ConnectionService()

            await service.connect(websocket)
            ```
        """
        await websocket.accept()

        self.active_connections.append(websocket)
        clients_count = len(self.active_connections)

        if clients_count == 1:
            if not self.had_connections:
                self.had_connections = True
                await self.emit(ConnectionEvent.FIRST_CONNECTION_EVER.value)
            await self.emit(ConnectionEvent.FIRST_ACTIVE_CONNECTION.value)
        self._log.info("Connected %s clients", clients_count)

    async def disconnect(self, websocket: WebSocket, should_close=True):
        """
        Handles the disconnection of a WebSocket connection. Removes the connection from the active
        connections list and attempts to close the WebSocket gracefully, if still connected.

        Emits:
            - `last_connection`: When the last active WebSocket connection is disconnected,
              leaving no clients connected.

        Args:
            websocket (WebSocket): The WebSocket connection object representing the client's disconnection.

        Side Effects:
            - Removes the WebSocket from the active connections list.
            - Closes the WebSocket connection gracefully, if it is still connected.
            - Emits relevant events based on connection state.

        Examples:
            ```python
            service = ConnectionService()

            await service.disconnect(websocket)
            ```
        """
        self.remove(websocket)

        if should_close and websocket.application_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except RuntimeError as ex:
                self._log.error(f"Failed to close weboscket due to RuntimeError: {ex}")

        clients_count = len(self.active_connections)
        self._log.info(f"Removing connection, total clients: {clients_count}")

        if clients_count == 0:
            await self.emit(ConnectionEvent.LAST_CONNECTION.value)

        self._log.info("Connected %s clients", clients_count)

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
            except RuntimeError as e:
                self._log.error("Broadcast runtime error %s", e)
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

    async def info(self, msg: str):
        """
        Broadcasts an informational (success) message to all connected WebSocket clients.

        The message will be displayed as a notification.
        """
        await self.broadcast_json({"type": "info", "payload": msg})

    async def error(self, msg: str):
        """
        Broadcasts an error message to all connected clients.

        The message will be shown as notification.
        """
        await self.broadcast_json({"type": "error", "payload": msg})

    async def warning(self, msg: str):
        """
        Broadcasts a warning message to all connected WebSocket clients.

        The message will be displayed as a notification.
        """
        await self.broadcast_json({"type": "warning", "payload": msg})
