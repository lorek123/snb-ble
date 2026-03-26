"""Custom exceptions for Storz & Bickel BLE library."""


class StorzBickelError(Exception):
    """Base exception for all Storz & Bickel BLE errors."""


class ConnectionError(StorzBickelError):
    """Raised when connection to device fails."""


class DeviceNotFoundError(StorzBickelError):
    """Raised when device cannot be found during scanning."""


class InvalidDataError(StorzBickelError):
    """Raised when received data is invalid or cannot be parsed."""


class CharacteristicReadError(InvalidDataError):
    """Raised when reading a BLE characteristic fails."""


class CharacteristicWriteError(InvalidDataError):
    """Raised when writing a BLE characteristic fails."""


class NotificationSetupError(InvalidDataError):
    """Raised when notification setup or teardown fails."""


class TimeoutError(StorzBickelError):
    """Raised when an operation times out."""


class CommandTimeoutError(TimeoutError):
    """Raised when a command response is not received within timeout."""


class FirmwareUpdateError(StorzBickelError):
    """Raised when firmware update fails.

    This is an experimental feature and may cause device damage if used incorrectly.
    """
