from enum import Enum


class ConnectionEvent(Enum):
    """Enumeration of connection-related events."""

    # Triggered when the first WebSocket connection is established in the application's lifecycle.
    FIRST_CONNECTION_EVER = "first_connection_ever"
    # Triggered when the first client connects (i.e., when active connections transition from 0 to 1).
    FIRST_ACTIVE_CONNECTION = "first_active_connection"
    # Triggered when the last active WebSocket connection is closed.
    LAST_CONNECTION = "last_connection"
