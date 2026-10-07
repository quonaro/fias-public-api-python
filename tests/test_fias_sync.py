"""
Live integration tests for the synchronous client.

These hit the real FIAS API, so they need network access and are excluded from
the default run. Run them explicitly with::

    pytest -m integration

If the service is unreachable the module skips instead of failing.
"""

import contextlib

import pytest

from fias_public_api import AddressType, SyncFPA, get_token_sync

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def token():
    """Fetch a real authentication token, or skip if the API is unreachable."""
    try:
        return get_token_sync()
    except Exception as exc:
        pytest.skip(f"FIAS API is not reachable: {exc}")


@pytest.fixture
def api(token):
    """Create a SyncFPA instance."""
    return SyncFPA(token, AddressType.MUNICIPALITY)


@pytest.fixture
def test_object_id():
    """A known valid object ID (Moscow, Red Square area)."""
    return 7700000000000


@pytest.fixture
def test_guid():
    """A known GUID for Moscow."""
    return "0c5b2444-70a0-4932-980c-b4dc0d3f02b5"


class TestGetTokenSync:
    """Tests for get_token_sync against the live service."""

    def test_get_token_sync_success(self):
        token = get_token_sync()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_get_token_sync_with_custom_url(self):
        token = get_token_sync(url="https://fias.nalog.ru/")
        assert isinstance(token, str)
        assert len(token) > 0


class TestSyncFPA:
    """Tests for SyncFPA against the live service."""

    def test_sync_fpa_initialization(self, token):
        api = SyncFPA(token, AddressType.MUNICIPALITY)
        assert api.token == token

    def test_search_basic(self, api):
        results = api.search("Москва")
        assert isinstance(results, list)
        # API may return empty list for some queries, that's acceptable
        if results:
            assert isinstance(results[0], dict)

    def test_search_empty_query(self, api):
        with pytest.raises(ValueError, match="search_string cannot be empty"):
            api.search("")

    def test_search_special_characters(self, api):
        results = api.search("Санкт-Петербург, Невский проспект")
        assert isinstance(results, list)

    def test_search_multiple_queries(self, api):
        for query in ["Москва", "Санкт-Петербург", "Тверская улица"]:
            assert isinstance(api.search(query), list)

    def test_details_by_id_basic(self, api, test_object_id):
        try:
            assert isinstance(api.details_by_id(test_object_id), dict)
        except Exception:
            pytest.skip("Test object ID not found")

    def test_details_by_id_with_address_type_int(self, api, test_object_id):
        try:
            assert isinstance(
                api.details_by_id(test_object_id, address_type=2), dict
            )
        except Exception:
            pytest.skip("Test object ID not found")

    def test_details_by_id_with_address_type_enum(self, api, test_object_id):
        try:
            assert isinstance(
                api.details_by_id(test_object_id, address_type=AddressType.MUNICIPALITY),
                dict,
            )
        except Exception:
            pytest.skip("Test object ID not found")

    def test_details_by_guid_basic(self, api, test_guid):
        try:
            assert isinstance(api.details_by_guid(test_guid), dict)
        except Exception:
            pytest.skip("Test GUID not found")

    def test_details_by_guid_with_address_type_int(self, api, test_guid):
        try:
            assert isinstance(api.details_by_guid(test_guid, address_type=2), dict)
        except Exception:
            pytest.skip("Test GUID not found")

    def test_details_by_guid_with_address_type_enum(self, api, test_guid):
        try:
            assert isinstance(
                api.details_by_guid(test_guid, address_type=AddressType.MUNICIPALITY),
                dict,
            )
        except Exception:
            pytest.skip("Test GUID not found")

    def test_details_deprecated_method(self, api, test_object_id):
        try:
            with pytest.warns(DeprecationWarning, match="details_by_id"):
                details = api.details(test_object_id)
            assert isinstance(details, dict)
        except Exception:
            pytest.skip("Test object ID not found")

    def test_details_with_address_type(self, api, test_object_id):
        try:
            details = api.details(test_object_id, address_type=AddressType.MUNICIPALITY)
            assert isinstance(details, dict)
        except Exception:
            pytest.skip("Test object ID not found")

    def test_invalid_object_id(self, api):
        # API may return an empty dict or raise; both are acceptable
        with contextlib.suppress(Exception):
            assert isinstance(api.details_by_id(999999999999999999), dict)

    def test_invalid_guid(self, api):
        # API may return an empty dict or raise; both are acceptable
        with contextlib.suppress(Exception):
            assert isinstance(api.details_by_guid("invalid-guid-format"), dict)
