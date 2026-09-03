import requests

# Connection-level failures (DNS resolution, refused connection, timeout).
CONNECTION_ERRORS = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)


class ApiConnectionError(AssertionError):
    """API unreachable (DNS/connection/timeout)."""


def _request(method: str, *args, **kwargs):
    try:
        return requests.request(method, *args, **kwargs)
    except CONNECTION_ERRORS as exc:
        raise ApiConnectionError(
            f"\nCannot reach the API: {type(exc).__name__}. "
            f"Check VPN/network connectivity and that the host is resolvable."
        ) from None


def get(*args, **kwargs):
    return _request('GET', *args, **kwargs)


def post(*args, **kwargs):
    return _request('POST', *args, **kwargs)
