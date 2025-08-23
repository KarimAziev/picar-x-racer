from typing import List, Optional


class RobotI2CError(Exception):
    """
    Base exception class for all Robot I2C-related errors.
    """

    def __init__(self, operation: str, addresses: List[int], message: str):
        super().__init__(message)
        self.operation = operation
        self.addresses = addresses
        self.message = message


class RobotI2CTimeout(RobotI2CError):
    """
    Exception raised for I2C timeouts during robot operations.
    """

    def __init__(self, operation: str, addresses: List[int]):
        super().__init__(
            operation,
            addresses,
            f"I2C timeout during '{operation}' (addresses: {', '.join([f'0x{addr:02X}' for addr in addresses])}).",
        )


class RobotI2CBusError(RobotI2CError):
    """
    Exception raised for I2C bus-related problems (e.g., device not found, remote I/O error).
    """

    def __init__(
        self,
        operation: str,
        addresses: List[int],
        errno: Optional[int],
        strerror: Optional[str],
    ):
        base_msg = f"I2C bus error during '{operation}' (addresses: {', '.join([f'0x{addr:02X}' for addr in addresses])})"
        parts = [
            base_msg,
            f"[Errno {errno}]" if errno is not None else None,
            f"{strerror}" if strerror else None,
        ]

        message = " ".join([item for item in parts if item])
        super().__init__(operation, addresses, message)
        self.errno = errno
        self.strerror = strerror


class ServoNotFoundError(ValueError):
    """
    Exception raised when the servo is not available.
    """

    pass


class MotorNotFoundError(ValueError):
    """
    Exception raised when the servo is not available.
    """

    pass
