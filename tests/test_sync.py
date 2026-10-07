"""
Tests for synchronous FIAS Public API client.

These are offline unit tests: every HTTP call is mocked, so they pass without
network access. The tests that talk to the live FIAS API live in
``test_fias_sync.py`` and are marked ``integration``.
"""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from fias_public_api import AddressType, SyncFPA, get_token_sync
from fias_public_api.constants import (
    DEFAULT_TIMEOUT,
    GET_ADDRESS_ITEMS,
    GET_REGIONS,
    STANDARD_HEADERS,
)
from tests.endpoints import IDS, PARAMS


def make_response(payload=None, status_code=200):
    """Build a stand-in for a requests.Response."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = json.dumps(payload)
    response.headers = {}
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def request_mock():
    """Patch the call the client actually makes: ``requests.request``."""
    with patch("fias_public_api.fias_sync.requests.request") as mock:
        yield mock


def call_args(request_mock):
    """Return the (method, url) positional args of the last request."""
    args, kwargs = request_mock.call_args
    return args, kwargs


class TestGetTokenSync:
    """Tests for get_token_sync function."""

    @patch("fias_public_api.fias_sync.requests.get")
    def test_get_token_success(self, mock_get):
        """Test successful token retrieval."""
        mock_get.return_value = make_response({"Token": "test-token-123"})

        assert get_token_sync() == "test-token-123"
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == DEFAULT_TIMEOUT

    @patch("fias_public_api.fias_sync.requests.get")
    def test_get_token_failure(self, mock_get):
        """Test token retrieval failure."""
        mock_get.return_value = make_response({"error": "nope"}, status_code=400)

        with pytest.raises(ValueError, match="Не удалось получить токен"):
            get_token_sync()

    @patch("fias_public_api.fias_sync.requests.get")
    def test_get_token_without_token_field(self, mock_get):
        """A 200 response without a Token field is a clear error, not a KeyError."""
        mock_get.return_value = make_response({"Settings": {}})

        with pytest.raises(ValueError, match="не содержит токен"):
            get_token_sync()

    @patch("fias_public_api.fias_sync.requests.get")
    def test_get_token_custom_timeout(self, mock_get):
        """Test token retrieval with an explicit timeout."""
        mock_get.return_value = make_response({"Token": "t"})

        get_token_sync(timeout=2.5)
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 2.5


class TestSyncFPA:
    """Tests for SyncFPA class."""

    @pytest.fixture
    def api(self):
        """Create SyncFPA instance for testing."""
        return SyncFPA(token="test-token", address_type=AddressType.MUNICIPALITY)

    @pytest.fixture
    def api_with_address_type(self):
        """Create SyncFPA instance with custom address type."""
        return SyncFPA(token="test-token", address_type=AddressType.ADMINISTRATIVE)

    def test_get_regions(self, api, request_mock):
        """Test get_regions method."""
        request_mock.return_value = make_response({"addresses": []})

        assert api.get_regions() == {"addresses": []}
        args, kwargs = call_args(request_mock)
        assert args == ("GET", GET_REGIONS)
        assert kwargs["headers"] == STANDARD_HEADERS("test-token")

    def test_every_request_carries_a_timeout(self, api, request_mock):
        """No request may be issued without a timeout."""
        request_mock.return_value = make_response({})

        api.get_regions()
        _, kwargs = call_args(request_mock)
        assert kwargs["timeout"] == DEFAULT_TIMEOUT

    def test_custom_timeout_is_used(self, request_mock):
        """The constructor timeout is applied to every request."""
        api = SyncFPA("test-token", AddressType.MUNICIPALITY, timeout=3.5)
        request_mock.return_value = make_response({})

        api.get_regions()
        _, kwargs = call_args(request_mock)
        assert kwargs["timeout"] == 3.5

    def test_http_error_is_raised(self, api, request_mock):
        """A failing status is raised, not returned as data."""
        response = make_response({"error": "unauthorized"}, status_code=401)
        response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        request_mock.return_value = response

        with pytest.raises(requests.HTTPError):
            api.get_regions()

    def test_http_error_is_raised_on_post(self, api, request_mock):
        """The POST path raises too, not just GET."""
        response = make_response({"error": "bad request"}, status_code=400)
        response.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")
        request_mock.return_value = response

        with pytest.raises(requests.HTTPError):
            api.get_address_items(address_level=1)

    @pytest.mark.parametrize(("call", "verb", "url"), PARAMS, ids=IDS)
    def test_every_endpoint_reaches_the_expected_url(
        self, api, request_mock, call, verb, url
    ):
        """The shared table, so sync and async cannot drift apart."""
        request_mock.return_value = make_response({})

        call(api)

        args, _ = call_args(request_mock)
        assert args == (verb.upper(), url)

    def test_get_address_items(self, api, request_mock):
        """Test get_address_items method."""
        request_mock.return_value = make_response({"addresses": []})

        result = api.get_address_items(
            path="test-path", address_level=1, name_part="test"
        )

        assert result == {"addresses": []}
        args, kwargs = call_args(request_mock)
        assert args == ("POST", GET_ADDRESS_ITEMS)
        assert kwargs["json"] == {
            "path": "test-path",
            "address_level": 1,
            "name_part": "test",
            "address_type": AddressType.MUNICIPALITY,
        }

    def test_get_address_items_omits_unset_filters(self, api, request_mock):
        """Filters left as None must not be sent."""
        request_mock.return_value = make_response({"addresses": []})

        api.get_address_items(address_level=7)

        _, kwargs = call_args(request_mock)
        assert kwargs["json"] == {
            "address_level": 7,
            "address_type": AddressType.MUNICIPALITY,
        }

    def test_get_address_items_sends_every_filter(self, api, request_mock):
        """Every optional filter reaches the payload."""
        request_mock.return_value = make_response({"addresses": []})

        api.get_address_items(
            path="path",
            address_level=1,
            address_levels=[1, 2],
            name_part="name",
            include_descendants=True,
        )

        _, kwargs = call_args(request_mock)
        assert kwargs["json"] == {
            "path": "path",
            "address_level": 1,
            "address_levels": [1, 2],
            "name_part": "name",
            "address_type": AddressType.MUNICIPALITY,
            "include_descendants": True,
        }

    def test_get_details(self, api, request_mock):
        """Test get_details method."""
        request_mock.return_value = make_response({"address_details": {}})

        assert api.get_details(object_id=12345) == {"address_details": {}}
        _, kwargs = call_args(request_mock)
        assert kwargs["params"] == {"object_id": 12345}

    def test_is_descendant(self, api, request_mock):
        """Test is_descendant method."""
        request_mock.return_value = make_response({"check": True})

        assert api.is_descendant(ancestor=1, descendant=2) == {"check": True}
        _, kwargs = call_args(request_mock)
        assert kwargs["params"] == {
            "ancestor": 1,
            "descendant": 2,
            "address_type": AddressType.MUNICIPALITY,
        }

    def test_has_descendants(self, api, request_mock):
        """Test has_descendants method."""
        request_mock.return_value = make_response({"check": True})

        assert api.has_descendants(parent=1, up_to_level=5) == {"check": True}
        _, kwargs = call_args(request_mock)
        assert kwargs["params"] == {
            "parent": 1,
            "up_to_level": 5,
            "address_type": AddressType.MUNICIPALITY,
        }

    def test_details_by_id(self, api, request_mock):
        """Test details_by_id method."""
        request_mock.return_value = make_response({"addresses": []})

        assert api.details_by_id(object_id=12345) == {"addresses": []}
        _, kwargs = call_args(request_mock)
        assert kwargs["params"]["object_id"] == 12345

    def test_details_by_id_with_address_type(
        self, api_with_address_type, request_mock
    ):
        """Test details_by_id with custom address type from constructor."""
        request_mock.return_value = make_response({"addresses": []})

        api_with_address_type.details_by_id(object_id=12345)

        _, kwargs = call_args(request_mock)
        assert kwargs["params"]["address_type"] == AddressType.ADMINISTRATIVE

    def test_details_by_id_overrides_address_type(self, api, request_mock):
        """A per-call address_type wins over the constructor default."""
        request_mock.return_value = make_response({"addresses": []})

        api.details_by_id(object_id=12345, address_type=AddressType.ADMINISTRATIVE)

        _, kwargs = call_args(request_mock)
        assert kwargs["params"]["address_type"] == AddressType.ADMINISTRATIVE

    def test_details_by_guid(self, api, request_mock):
        """Test details_by_guid method."""
        request_mock.return_value = make_response({"addresses": []})

        assert api.details_by_guid(object_guid="test-guid") == {"addresses": []}
        _, kwargs = call_args(request_mock)
        assert kwargs["params"]["object_guid"] == "test-guid"

    def test_get_address_item_by_cadastral_number(self, api, request_mock):
        """Test get_address_item_by_cadastral_number method."""
        request_mock.return_value = make_response({"addresses": []})

        api.get_address_item_by_cadastral_number(cadastral_number="123:45:678:90")

        _, kwargs = call_args(request_mock)
        assert kwargs["params"]["cadastral_number"] == "123:45:678:90"

    def test_get_fias_object_types(self, api, request_mock):
        """Test get_fias_object_types method."""
        request_mock.return_value = make_response({"types": []})

        assert api.get_fias_object_types() == {"types": []}

    def test_search_address_items(self, api, request_mock):
        """Test search_address_items method."""
        request_mock.return_value = make_response({"addresses": []})

        assert api.search_address_items(search_string="Москва") == {"addresses": []}
        _, kwargs = call_args(request_mock)
        assert kwargs["params"]["search_string"] == "Москва"

    def test_search_address_items_empty_query(self, api, request_mock):
        """An empty query fails locally, without touching the network."""
        with pytest.raises(ValueError, match="search_string cannot be empty"):
            api.search_address_items(search_string="   ")

        request_mock.assert_not_called()

    def test_get_address_hint_get(self, api, request_mock):
        """Test get_address_hint with GET request."""
        request_mock.return_value = make_response({"hints": []})

        assert api.get_address_hint(search_string="Москва") == {"hints": []}
        args, kwargs = call_args(request_mock)
        assert args[0] == "GET"
        assert kwargs["params"]["search_string"] == "Москва"

    def test_get_address_hint_post(self, api, request_mock):
        """Test get_address_hint with POST request."""
        request_mock.return_value = make_response({"hints": []})

        assert api.get_address_hint(up_to_level=5, search_non_active=False) == {
            "hints": []
        }
        args, kwargs = call_args(request_mock)
        assert args[0] == "POST"
        assert kwargs["json"] == {
            "searchNonActive": False,
            "addressType": AddressType.MUNICIPALITY,
            "upToLevel": 5,
        }

    def test_get_address_hint_post_sends_locations_boost(self, api, request_mock):
        """The optional boost and non-active flag reach the payload."""
        request_mock.return_value = make_response({"hints": []})

        api.get_address_hint(up_to_level=5, locations_boost=1, search_non_active=True)

        _, kwargs = call_args(request_mock)
        assert kwargs["json"] == {
            "searchNonActive": True,
            "addressType": AddressType.MUNICIPALITY,
            "upToLevel": 5,
            "locationsBoost": 1,
        }

    def test_get_address_hint_rejects_an_empty_query(self, api, request_mock):
        """A blank hint query fails locally, without touching the network."""
        with pytest.raises(ValueError, match="search_string cannot be empty"):
            api.get_address_hint(search_string="  ")

        request_mock.assert_not_called()

    def test_search_address_item_rejects_an_empty_query(self, api, request_mock):
        """A blank single-item query fails locally, without touching the network."""
        with pytest.raises(ValueError, match="search_string cannot be empty"):
            api.search_address_item(search_string="")

        request_mock.assert_not_called()

    def test_search_address_item(self, api, request_mock):
        """Test search_address_item method."""
        request_mock.return_value = make_response({"object_id": 12345})

        assert api.search_address_item(search_string="Москва") == {"object_id": 12345}

    def test_get_location_by_ip(self, api, request_mock):
        """Test get_location_by_ip method."""
        request_mock.return_value = make_response({"addresses": []})

        assert api.get_location_by_ip(ip="8.8.8.8") == {"addresses": []}
        _, kwargs = call_args(request_mock)
        assert kwargs["params"]["ip"] == "8.8.8.8"

    def test_search(self, api, request_mock):
        """Test search method (wrapper over get_address_hint)."""
        request_mock.return_value = make_response({"hints": [{"id": 1}]})

        assert api.search(search_string="Москва") == [{"id": 1}]

    def test_search_returns_empty_list_when_no_hints(self, api, request_mock):
        """A response without hints yields an empty list, not a KeyError."""
        request_mock.return_value = make_response({})

        assert api.search(search_string="Москва") == []

    def test_details_is_deprecated(self, api, request_mock):
        """The deprecated method warns instead of printing to stdout."""
        request_mock.return_value = make_response({"addresses": []})

        with pytest.warns(DeprecationWarning, match="details_by_id"):
            result = api.details(object_id=12345)

        assert result == {"addresses": []}
        _, kwargs = call_args(request_mock)
        assert kwargs["params"]["object_id"] == 12345

    def test_get_address_type_default(self, api):
        """Test _get_address_type with default value."""
        assert api._get_address_type(None) == AddressType.MUNICIPALITY

    def test_get_address_type_custom(self, api):
        """Test _get_address_type with custom value."""
        assert (
            api._get_address_type(AddressType.ADMINISTRATIVE)
            == AddressType.ADMINISTRATIVE
        )
        assert api._get_address_type(1) == 1
