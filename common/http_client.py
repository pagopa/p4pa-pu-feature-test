import requests

# Connection-level failures (DNS resolution, refused connection, timeout).
CONNECTION_ERRORS = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)


class ApiConnectionError(AssertionError):
    """API unreachable (DNS/connection/timeout)."""


def _request(method: str, **kwargs):
    try:
        return requests.request(method, **kwargs)
    except CONNECTION_ERRORS as exc:
        raise ApiConnectionError(
            f"\nCannot reach the API: {type(exc).__name__}. "
            f"Check VPN/network connectivity and that the host is resolvable."
        ) from None


def get(**kwargs):
    return _request('GET', **kwargs)


def post(**kwargs):
    return _request('POST', **kwargs)
