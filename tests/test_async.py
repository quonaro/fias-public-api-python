"""
Tests for asynchronous FIAS Public API client.

These are offline unit tests: the httpx client is replaced, so they pass without
network access. The tests that talk to the live FIAS API live in
``test_fias_async.py`` and are marked ``integration``.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from fias_public_api import AddressType, AsyncFPA, get_token_async
from fias_public_api.constants import DEFAULT_TIMEOUT, GET_REGIONS
from tests.endpoints import IDS, PARAMS


def make_response(payload=None, status_code=200):
    """Build a real httpx.Response, so raise_for_status behaves as in production."""
    request = httpx.Request("GET", "https://fias-public-service.nalog.ru/")
    return httpx.Response(status_code, json=payload, request=request)


class TestGetTokenAsync:
    """Tests for get_token_async function."""

    @pytest.mark.asyncio
    @patch("fias_public_api.fias_async.httpx.AsyncClient")
    async def test_get_token_success(self, mock_client_class):
        """Test successful token retrieval."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Token": "test-token-123"}
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        token = await get_token_async()
        assert token == "test-token-123"
        _, kwargs = mock_client_class.call_args
        assert kwargs["timeout"] == DEFAULT_TIMEOUT

    @pytest.mark.asyncio
    @patch("fias_public_api.fias_async.httpx.AsyncClient")
    async def test_get_token_failure(self, mock_client_class):
        """Test token retrieval failure."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        with pytest.raises(ValueError, match="Не удалось получить токен"):
            await get_token_async()

    @pytest.mark.asyncio
    @patch("fias_public_api.fias_async.httpx.AsyncClient")
    async def test_get_token_without_token_field(self, mock_client_class):
        """A 200 response without a Token field is a clear error, not a KeyError."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Settings": {}}
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        with pytest.raises(ValueError, match="не содержит токен"):
            await get_token_async()


class TestAsyncFPA:
    """Tests for AsyncFPA class."""

    @pytest.fixture
    def api(self):
        """Create AsyncFPA instance for testing."""
        return AsyncFPA(token="test-token", address_type=AddressType.MUNICIPALITY)

    @pytest.fixture
    def api_with_address_type(self):
        """Create AsyncFPA instance with custom address type."""
        return AsyncFPA(token="test-token", address_type=AddressType.ADMINISTRATIVE)

    def stub_client(self, api, response, method="get"):
        """Point the client at a stub transport and return the stub."""
        client = AsyncMock()
        setattr(client, method, AsyncMock(return_value=response))
        api._client = client
        return client

    @pytest.mark.asyncio
    async def test_get_regions(self, api):
        """Test get_regions method."""
        client = self.stub_client(api, make_response({"addresses": []}))

        assert await api.get_regions() == {"addresses": []}
        client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_address_items(self, api):
        """Test get_address_items method."""
        client = self.stub_client(api, make_response({"addresses": []}), "post")

        assert await api.get_address_items(path="test-path", address_level=1) == {
            "addresses": []
        }
        _, kwargs = client.post.call_args
        assert kwargs["json"]["path"] == "test-path"
        assert kwargs["json"]["address_type"] == AddressType.MUNICIPALITY

    @pytest.mark.asyncio
    async def test_get_address_items_sends_every_filter(self, api):
        """Every optional filter reaches the payload."""
        client = self.stub_client(api, make_response({}), "post")

        await api.get_address_items(
            path="path",
            address_level=1,
            address_levels=[1, 2],
            name_part="name",
            include_descendants=True,
        )

        _, kwargs = client.post.call_args
        assert kwargs["json"] == {
            "path": "path",
            "address_level": 1,
            "address_levels": [1, 2],
            "name_part": "name",
            "address_type": AddressType.MUNICIPALITY,
            "include_descendants": True,
        }

    @pytest.mark.asyncio
    async def test_get_details(self, api):
        """Test get_details method."""
        client = self.stub_client(api, make_response({"address_details": {}}))

        assert await api.get_details(object_id=12345) == {"address_details": {}}
        _, kwargs = client.get.call_args
        assert kwargs["params"] == {"object_id": 12345}

    @pytest.mark.asyncio
    async def test_details_by_id_with_address_type(self, api_with_address_type):
        """Test details_by_id with custom address type from constructor."""
        client = self.stub_client(api_with_address_type, make_response({"addresses": []}))

        result = await api_with_address_type.details_by_id(object_id=12345)

        assert result == {"addresses": []}
        _, kwargs = client.get.call_args
        assert kwargs["params"]["address_type"] == AddressType.ADMINISTRATIVE

    @pytest.mark.asyncio
    async def test_search(self, api):
        """Test search method."""
        self.stub_client(api, make_response({"hints": [{"id": 1}]}))

        assert await api.search(search_string="Москва") == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_search_empty_query(self, api):
        """An empty query fails locally, without touching the network."""
        client = self.stub_client(api, make_response({"hints": []}))

        with pytest.raises(ValueError, match="search_string cannot be empty"):
            await api.search("   ")

        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_address_items_rejects_an_empty_query(self, api):
        """A blank query fails locally, without touching the network."""
        client = self.stub_client(api, make_response({}))

        with pytest.raises(ValueError, match="search_string cannot be empty"):
            await api.search_address_items(search_string="   ")

        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_address_hint_post_sends_locations_boost(self, api):
        """The optional boost and non-active flag reach the payload."""
        client = self.stub_client(api, make_response({}), "post")

        await api.get_address_hint(
            up_to_level=5, locations_boost=1, search_non_active=True
        )

        _, kwargs = client.post.call_args
        assert kwargs["json"] == {
            "searchNonActive": True,
            "addressType": AddressType.MUNICIPALITY,
            "upToLevel": 5,
            "locationsBoost": 1,
        }

    @pytest.mark.asyncio
    async def test_get_address_hint_rejects_an_empty_query(self, api):
        """A blank hint query fails locally, without touching the network."""
        client = self.stub_client(api, make_response({}))

        with pytest.raises(ValueError, match="search_string cannot be empty"):
            await api.get_address_hint(search_string="  ")

        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_address_item_rejects_an_empty_query(self, api):
        """A blank single-item query fails locally, without touching the network."""
        client = self.stub_client(api, make_response({}))

        with pytest.raises(ValueError, match="search_string cannot be empty"):
            await api.search_address_item(search_string="")

        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_http_error_is_raised(self, api):
        """A failing status is raised, not returned as data."""
        self.stub_client(api, make_response({"error": "unauthorized"}, status_code=401))

        with pytest.raises(httpx.HTTPStatusError):
            await api.get_regions()

    @pytest.mark.asyncio
    async def test_unsupported_method_is_rejected(self, api):
        """A verb the client does not know is refused instead of silently sent."""
        self.stub_client(api, make_response({}))

        with pytest.raises(ValueError, match="unsupported method"):
            await api._make_request("PATCH", GET_REGIONS)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("call", "verb", "url"), PARAMS, ids=IDS)
    async def test_every_endpoint_reaches_the_expected_url(
        self, api, call, verb, url
    ):
        """The shared table, so sync and async cannot drift apart."""
        client = AsyncMock()
        client.get = AsyncMock(return_value=make_response({}))
        client.post = AsyncMock(return_value=make_response({}))
        api._client = client

        await call(api)

        args, _ = getattr(client, verb).call_args
        assert args[0] == url

    @pytest.mark.asyncio
    async def test_client_is_created_with_the_timeout(self):
        """The constructor timeout reaches the httpx client."""
        api = AsyncFPA("test-token", AddressType.MUNICIPALITY, timeout=3.5)

        with patch("fias_public_api.fias_async.httpx.AsyncClient") as mock_client_class:
            assert api.client is not None
            _, kwargs = mock_client_class.call_args
            assert kwargs["timeout"] == 3.5

    @pytest.mark.asyncio
    async def test_details_is_deprecated(self, api):
        """The deprecated method warns instead of printing to stdout."""
        self.stub_client(api, make_response({"addresses": []}))

        with pytest.warns(DeprecationWarning, match="details_by_id"):
            result = await api.details(object_id=12345)

        assert result == {"addresses": []}

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        api = AsyncFPA(token="test-token", address_type=AddressType.MUNICIPALITY)

        async with api:
            assert api._client is not None
            assert api.client is not None

        # After context exit, client should be closed and dropped
        assert api._client is None

    @pytest.mark.asyncio
    async def test_exit_without_entering_is_a_no_op(self):
        """__aexit__ guards against a client that was never created."""
        api = AsyncFPA(token="test-token", address_type=AddressType.MUNICIPALITY)

        await api.__aexit__(None, None, None)

        assert api._client is None

    @pytest.mark.asyncio
    async def test_client_is_recreated_after_close(self):
        """Reusing a client that left its context must not hit a closed transport."""
        api = AsyncFPA(token="test-token", address_type=AddressType.MUNICIPALITY)

        async with api:
            first = api.client

        assert api._client is None
        second = api.client
        assert second is not first
        await second.aclose()

    def test_get_address_type_default(self, api):
        """Test _get_address_type with default value."""
        assert api._get_address_type(None) == AddressType.MUNICIPALITY

    def test_get_address_type_custom(self, api):
        """Test _get_address_type with custom value."""
        assert (
            api._get_address_type(AddressType.ADMINISTRATIVE)
            == AddressType.ADMINISTRATIVE
        )
