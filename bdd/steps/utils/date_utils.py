from datetime import datetime


def today() -> str:
    """Current date formatted as 'YYYY-MM-DD'."""
    return datetime.now().strftime('%Y-%m-%d')


def now() -> str:
    """Current date-time formatted as 'YYYY-MM-DDTHH:MM:SS' (local, no microseconds)."""
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


def unique_timestamp() -> str:
    """15-character timestamp ('YYYYMMDDHHMMSS' plus one sub-second digit), used as a
    near-unique component when building test identifiers."""
    return datetime.now().strftime('%Y%m%d%H%M%S%f')[:15]
