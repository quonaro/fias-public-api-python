from importlib.metadata import PackageNotFoundError, version

from . import constants, fias_async, fias_sync
from .constants import (
    DEFAULT_RETRY_EXCEPTIONS,
    DEFAULT_TIMEOUT,
    STANDARD_HEADERS,
    STANDART_HEADERS,
    AddressType,
    retry_on_error,
)
from .fias_async import AsyncFPA, get_token_async
from .fias_sync import SyncFPA, get_token_sync

try:
    __version__ = version("fias-public-api")
except PackageNotFoundError:  # running from a source tree without the dist
    __version__ = "0.0.0"

__all__ = [
    "DEFAULT_RETRY_EXCEPTIONS",
    "DEFAULT_TIMEOUT",
    "STANDARD_HEADERS",
    "STANDART_HEADERS",
    "AddressType",
    "retry_on_error",
    "get_token_async",
    "get_token_sync",
    "AsyncFPA",
    "SyncFPA",
    "constants",
    "fias_async",
    "fias_sync",
    "__version__",
]
