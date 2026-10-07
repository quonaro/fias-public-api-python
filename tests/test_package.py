"""
Tests for the package surface: the reported version, the exported names, and
the symmetry between the two clients.
"""

import importlib
from importlib.metadata import PackageNotFoundError, version

import pytest

import fias_public_api
from fias_public_api import AsyncFPA, SyncFPA
from tests.endpoints import METHODS, NOT_IN_TABLE


def test_version_matches_the_installed_distribution():
    """The version is read from the distribution, so it cannot drift."""
    assert fias_public_api.__version__ == version("fias-public-api")


def test_version_falls_back_when_the_distribution_is_missing(monkeypatch):
    """Running from a source tree without the dist installed must not explode."""

    def missing(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr("importlib.metadata.version", missing)
    try:
        reloaded = importlib.reload(fias_public_api)
        assert reloaded.__version__ == "0.0.0"
    finally:
        # Put the real version back so the rest of the suite sees it.
        monkeypatch.undo()
        importlib.reload(fias_public_api)

    assert fias_public_api.__version__ == version("fias-public-api")


@pytest.mark.parametrize("name", fias_public_api.__all__)
def test_every_exported_name_exists(name):
    assert hasattr(fias_public_api, name)


def test_sync_and_async_expose_the_same_methods():
    """The two clients are meant to be interchangeable apart from the transport."""
    sync = {name for name in dir(SyncFPA) if not name.startswith("_")}
    async_ = {name for name in dir(AsyncFPA) if not name.startswith("_")}

    # The async client additionally exposes the lazily created httpx client.
    assert sync == async_ - {"client"}


def test_the_endpoint_table_covers_every_client_method():
    """A new endpoint must join the shared table, or it ships untested."""
    public = {
        name
        for name in dir(SyncFPA)
        if not name.startswith("_") and callable(getattr(SyncFPA, name))
    }

    assert public - METHODS - NOT_IN_TABLE == set()
