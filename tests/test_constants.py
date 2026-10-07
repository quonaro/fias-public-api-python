"""
Tests for constants module.
"""

import httpx
import pytest
import requests

from fias_public_api import (
    STANDARD_HEADERS,
    STANDART_HEADERS,
    AddressType,
    retry_on_error,
)
from fias_public_api.constants import DEFAULT_RETRY_EXCEPTIONS


class TestAddressType:
    """Tests for AddressType enum."""

    def test_address_type_values(self):
        """Test AddressType enum values."""
        assert AddressType.ADMINISTRATIVE == 1
        assert AddressType.MUNICIPALITY == 2

    def test_address_type_int_conversion(self):
        """Test AddressType can be used as int."""
        assert int(AddressType.ADMINISTRATIVE) == 1
        assert int(AddressType.MUNICIPALITY) == 2


class TestStandardHeaders:
    """Tests for STANDARD_HEADERS function."""

    def test_standard_headers(self):
        """Test STANDARD_HEADERS function."""
        token = "test-token-123"
        headers = STANDARD_HEADERS(token)

        assert headers["accept"] == "application/json"
        assert headers["master-token"] == token
        assert headers["Content-Type"] == "application/json"

    def test_legacy_misspelled_name_is_the_same_function(self):
        """STANDART_HEADERS is kept as an alias of STANDARD_HEADERS."""
        assert STANDART_HEADERS is STANDARD_HEADERS


class TestRetryOnError:
    """Tests for retry_on_error decorator."""

    def test_the_default_set_covers_both_http_libraries(self):
        """The default must retry what either client raises on the wire."""
        for exc in (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.HTTPStatusError,
        ):
            assert issubclass(exc, DEFAULT_RETRY_EXCEPTIONS), exc

    def test_the_default_set_excludes_programming_errors(self):
        for exc in (ValueError, KeyError, TypeError):
            assert not issubclass(exc, DEFAULT_RETRY_EXCEPTIONS), exc

    def test_an_httpx_transport_error_is_retried_by_default(self):
        """httpx errors are not OSError subclasses, so they need naming."""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Test error")

        with pytest.raises(httpx.ConnectError, match="Test error"):
            test_func()
        assert call_count == 3

    def test_retry_on_error_success(self):
        """Test retry decorator with successful call."""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        assert test_func() == "success"
        assert call_count == 1

    def test_retry_on_error_retry(self):
        """Transport errors are retried by default."""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Test error")
            return "success"

        assert test_func() == "success"
        assert call_count == 2

    def test_retry_on_error_does_not_retry_programming_errors(self):
        """ValueError is not retried: repeating it cannot succeed."""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_func()
        assert call_count == 1

    def test_retry_on_error_explicit_exceptions(self):
        """An explicit exception tuple widens what is retried."""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.1, exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_func()
        assert call_count == 3

    def test_retry_on_error_max_retries(self):
        """Test retry decorator with max retries exceeded."""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Test error")

        with pytest.raises(ConnectionError, match="Test error"):
            test_func()
        assert call_count == 3

    def test_retry_on_error_rejects_a_useless_retry_count(self):
        """max_retries=0 used to return None instead of raising."""
        with pytest.raises(ValueError, match="max_retries must be at least 1"):
            retry_on_error(max_retries=0)

    def test_retry_on_error_with_a_single_attempt(self):
        """max_retries=1 means one attempt and no sleep."""
        call_count = 0

        @retry_on_error(max_retries=1, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Test error")

        with pytest.raises(ConnectionError, match="Test error"):
            test_func()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_error_async_max_retries(self):
        """The async wrapper re-raises once the attempts are exhausted."""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Test error")

        with pytest.raises(ConnectionError, match="Test error"):
            await test_func()
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_error_async(self):
        """Test retry decorator with an async function."""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Test error")
            return "success"

        assert await test_func() == "success"
        assert call_count == 2
