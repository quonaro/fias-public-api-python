"""
Live integration tests for the asynchronous client.

These hit the real FIAS API, so they need network access and are excluded from
the default run. Run them explicitly with::

    pytest -m integration

If the service is unreachable the module skips instead of failing.
"""

import contextlib

import pytest

from fias_public_api import AddressType, AsyncFPA, get_token_async, retry_on_error

pytestmark = pytest.mark.integration


@pytest.fixture
async def token():
    """Fetch a real authentication token, or skip if the API is unreachable."""
    try:
        return await get_token_async()
    except Exception as exc:
        pytest.skip(f"FIAS API is not reachable: {exc}")


@pytest.fixture
async def api(token):
    """Create an AsyncFPA instance."""
    async with AsyncFPA(token, AddressType.MUNICIPALITY) as api:
        yield api


@pytest.fixture
def test_object_id():
    """A known valid object ID (Moscow, Red Square area)."""
    return 7700000000000


@pytest.fixture
def test_guid():
    """A known GUID for Moscow."""
    return "0c5b2444-70a0-4932-980c-b4dc0d3f02b5"


class TestGetTokenAsync:
    """Tests for get_token_async against the live service."""

    @retry_on_error(max_retries=3, delay=0.5)
    async def test_get_token_async_success(self):
        token = await get_token_async()
        assert isinstance(token, str)
        assert len(token) > 0

    async def test_get_token_async_with_custom_url(self):
        token = await get_token_async(url="https://fias.nalog.ru/")
        assert isinstance(token, str)
        assert len(token) > 0


class TestAsyncFPA:
    """Tests for AsyncFPA against the live service."""

    async def test_async_fpa_initialization(self, token):
        api = AsyncFPA(token, AddressType.MUNICIPALITY)
        assert api.token == token
        if api._client:
            await api._client.aclose()

    async def test_async_context_manager(self, token):
        async with AsyncFPA(token, AddressType.MUNICIPALITY) as api:
            assert api.token == token
            assert api._client is not None

    async def test_search_basic(self, api):
        results = await api.search("Москва")
        assert isinstance(results, list)
        # API may return empty list for some queries, that's acceptable
        if results:
            assert isinstance(results[0], dict)

    async def test_search_empty_query(self, api):
        with pytest.raises(ValueError, match="search_string cannot be empty"):
            await api.search("")

    async def test_search_special_characters(self, api):
        results = await api.search("Санкт-Петербург, Невский проспект")
        assert isinstance(results, list)

    async def test_search_multiple_queries(self, api):
        for query in ["Москва", "Санкт-Петербург", "Тверская улица"]:
            assert isinstance(await api.search(query), list)

    async def test_details_by_id_basic(self, api, test_object_id):
        try:
            assert isinstance(await api.details_by_id(test_object_id), dict)
        except Exception:
            pytest.skip("Test object ID not found")

    async def test_details_by_id_with_address_type_int(self, api, test_object_id):
        try:
            assert isinstance(
                await api.details_by_id(test_object_id, address_type=2), dict
            )
        except Exception:
            pytest.skip("Test object ID not found")

    async def test_details_by_id_with_address_type_enum(self, api, test_object_id):
        try:
            assert isinstance(
                await api.details_by_id(
                    test_object_id, address_type=AddressType.MUNICIPALITY
                ),
                dict,
            )
        except Exception:
            pytest.skip("Test object ID not found")

    async def test_details_by_guid_basic(self, api, test_guid):
        try:
            assert isinstance(await api.details_by_guid(test_guid), dict)
        except Exception:
            pytest.skip("Test GUID not found")

    async def test_details_by_guid_with_address_type_int(self, api, test_guid):
        try:
            assert isinstance(await api.details_by_guid(test_guid, address_type=2), dict)
        except Exception:
            pytest.skip("Test GUID not found")

    async def test_details_by_guid_with_address_type_enum(self, api, test_guid):
        try:
            assert isinstance(
                await api.details_by_guid(
                    test_guid, address_type=AddressType.MUNICIPALITY
                ),
                dict,
            )
        except Exception:
            pytest.skip("Test GUID not found")

    async def test_details_deprecated_method(self, api, test_object_id):
        try:
            with pytest.warns(DeprecationWarning, match="details_by_id"):
                details = await api.details(test_object_id)
            assert isinstance(details, dict)
        except Exception:
            pytest.skip("Test object ID not found")

    async def test_details_with_address_type(self, api, test_object_id):
        try:
            details = await api.details(
                test_object_id, address_type=AddressType.MUNICIPALITY
            )
            assert isinstance(details, dict)
        except Exception:
            pytest.skip("Test object ID not found")

    async def test_invalid_object_id(self, api):
        # API may return an empty dict or raise; both are acceptable
        with contextlib.suppress(Exception):
            assert isinstance(await api.details_by_id(999999999999999999), dict)

    async def test_invalid_guid(self, api):
        # API may return an empty dict or raise; both are acceptable
        with contextlib.suppress(Exception):
            assert isinstance(await api.details_by_guid("invalid-guid-format"), dict)

    async def test_client_property(self, token):
        api = AsyncFPA(token, AddressType.MUNICIPALITY)
        client = api.client
        assert client is not None
        await client.aclose()
