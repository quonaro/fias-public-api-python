"""
Tests for the logging layer: the JSON formatter, credential redaction, the
console handler, the method-call decorator, and the request/response records.
"""

import json
import logging
import re
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest
from requests import HTTPError

from fias_public_api import AddressType, AsyncFPA, SyncFPA
from fias_public_api.constants import (
    GET_REGIONS,
    STANDARD_HEADERS,
    JsonFormatter,
    _safe_headers,
    _truncate_body,
    enable_console_logging,
    log_method_call,
)

SYNC_LOGGER = "fias_public_api.fias_sync"
ASYNC_LOGGER = "fias_public_api.fias_async"

TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}(?:[+-]\d{2}:\d{2})?$")


def make_record(message="http request", level=logging.INFO, **data):
    """Build a log record, optionally carrying the `data` payload the handler adds."""
    record = logging.LogRecord("test", level, "", 0, message, (), None)
    if data:
        record.data = data
    return record


def sync_response(payload=None, status_code=200):
    """A stand-in for a requests.Response."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = json.dumps(payload)
    response.headers = {"content-type": "application/json"}
    response.raise_for_status = Mock()
    return response


def async_response(payload=None, status_code=200):
    """A real httpx.Response, so text and headers behave as in production."""
    request = httpx.Request("GET", "https://fias-public-service.nalog.ru/")
    return httpx.Response(status_code, json=payload, request=request)


def logged_records(caplog):
    """The records that carry an HTTP payload."""
    return [r for r in caplog.records if isinstance(getattr(r, "data", None), dict)]


class TestJsonFormatter:
    """Tests for the JSON console formatter."""

    def test_formats_a_record_as_a_single_json_line(self):
        line = JsonFormatter().format(make_record("http request"))

        assert "\n" not in line
        payload = json.loads(line)
        assert payload["msg"] == "http request"
        assert payload["level"] == "INFO"

    def test_merges_the_data_payload(self):
        record = make_record("http request", method="GET", url="https://example.com")

        payload = json.loads(JsonFormatter().format(record))

        assert payload["method"] == "GET"
        assert payload["url"] == "https://example.com"

    def test_ignores_a_data_attribute_that_is_not_a_dict(self):
        record = make_record("hello")
        record.data = "not a mapping"

        assert json.loads(JsonFormatter().format(record))["msg"] == "hello"

    def test_serialises_values_json_cannot_handle(self):
        record = make_record("hello", value=object())

        assert "object object" in json.loads(JsonFormatter().format(record))["value"]

    def test_timestamp_is_iso_with_milliseconds(self):
        payload = json.loads(JsonFormatter().format(make_record()))

        assert TIMESTAMP.match(payload["time"]), payload["time"]


class TestSafeHeaders:
    """Tests for credential redaction in logged headers."""

    def test_redacts_token_secret_and_authorization(self):
        safe = _safe_headers(
            {
                "master-token": "secret-value",
                "Authorization": "Bearer x",
                "X-Secret": "y",
            }
        )

        assert safe == {
            "master-token": "[REDACTED]",
            "Authorization": "[REDACTED]",
            "X-Secret": "[REDACTED]",
        }

    def test_keeps_ordinary_headers(self):
        safe = _safe_headers({"accept": "application/json", "Content-Type": "text/x"})

        assert safe == {"accept": "application/json", "Content-Type": "text/x"}

    def test_the_real_token_never_survives(self):
        token = "super-secret-token"

        assert token not in json.dumps(_safe_headers(STANDARD_HEADERS(token)))

    def test_handles_an_empty_mapping(self):
        assert _safe_headers({}) == {}


class TestTruncateBody:
    """Tests for the logged body truncation."""

    def test_short_body_is_untouched(self):
        assert _truncate_body("abc") == "abc"

    def test_body_at_the_limit_is_untouched(self):
        assert _truncate_body("x" * 10, max_len=10) == "x" * 10

    def test_long_body_is_truncated(self):
        truncated = _truncate_body("x" * 50, max_len=10)

        assert truncated == "x" * 10 + "..."
        assert len(truncated) < 50

    def test_non_string_body_is_stringified(self):
        assert _truncate_body({"a": 1}) == "{'a': 1}"


class TestEnableConsoleLogging:
    """Tests for the once-only console handler."""

    @pytest.fixture
    def logger(self):
        """A logger nobody else uses, so the handler state starts clean."""
        return logging.getLogger(f"fias_public_api.test.{uuid4().hex}")

    def test_attaches_exactly_one_handler(self, logger):
        enable_console_logging(logger, logging.INFO)
        enable_console_logging(logger, logging.INFO)
        enable_console_logging(logger, logging.DEBUG)

        assert len(logger.handlers) == 1

    def test_sets_the_level_on_logger_and_handler(self, logger):
        enable_console_logging(logger, logging.WARNING)

        assert logger.level == logging.WARNING
        assert logger.handlers[0].level == logging.WARNING

    def test_handler_uses_the_json_formatter(self, logger):
        enable_console_logging(logger)

        assert isinstance(logger.handlers[0].formatter, JsonFormatter)

    def test_repeated_calls_do_not_duplicate_lines(self, logger, capsys):
        enable_console_logging(logger)
        enable_console_logging(logger)

        logger.info("one line")

        assert capsys.readouterr().out.count("one line") == 1


class Subject:
    """A minimal object with a logger, used to exercise the decorator."""

    def __init__(self, logger):
        self._logger = logger

    @log_method_call()
    def ok(self, value, token=None):
        return value * 2

    @log_method_call()
    def boom(self):
        raise RuntimeError("nope")

    @log_method_call()
    async def aok(self, value, token=None):
        return value

    @log_method_call()
    async def aboom(self):
        raise RuntimeError("nope")


class TestLogMethodCall:
    """Tests for the log_method_call decorator."""

    @pytest.fixture
    def subject(self):
        return Subject(logging.getLogger(f"fias_public_api.test.{uuid4().hex}"))

    def test_logs_the_call_and_the_result(self, subject, caplog):
        with caplog.at_level(logging.DEBUG, logger=subject._logger.name):
            assert subject.ok(21) == 42

        assert "Subject.ok called" in caplog.text
        assert "Subject.ok completed successfully" in caplog.text

    def test_logs_the_exception_and_reraises(self, subject, caplog):
        with (
            caplog.at_level(logging.DEBUG, logger=subject._logger.name),
            pytest.raises(RuntimeError, match="nope"),
        ):
            subject.boom()

        assert "Subject.boom raised RuntimeError: nope" in caplog.text

    def test_token_kwargs_are_kept_out_of_the_log(self, subject, caplog):
        with caplog.at_level(logging.DEBUG, logger=subject._logger.name):
            subject.ok(21, token="super-secret")

        assert "super-secret" not in caplog.text

    async def test_async_wrapper_logs_the_result(self, subject, caplog):
        with caplog.at_level(logging.DEBUG, logger=subject._logger.name):
            assert await subject.aok(1) == 1

        assert "Subject.aok completed successfully" in caplog.text

    async def test_async_wrapper_logs_and_reraises(self, subject, caplog):
        with (
            caplog.at_level(logging.DEBUG, logger=subject._logger.name),
            pytest.raises(RuntimeError, match="nope"),
        ):
            await subject.aboom()

        assert "Subject.aboom raised RuntimeError: nope" in caplog.text


class TestClientRequestLogging:
    """The request/response records the clients emit."""

    @pytest.fixture
    def request_mock(self):
        with patch("fias_public_api.fias_sync.requests.request") as mock:
            yield mock

    def test_sync_logs_the_request_and_the_response(self, request_mock, caplog):
        request_mock.return_value = sync_response({"addresses": []})
        api = SyncFPA("token-value", AddressType.ADMINISTRATIVE)

        with caplog.at_level(logging.DEBUG, logger=SYNC_LOGGER):
            api.get_regions()

        records = logged_records(caplog)
        assert [r.getMessage() for r in records] == ["http request", "http response"]
        assert records[0].data["method"] == "GET"
        assert records[0].data["url"] == GET_REGIONS
        assert records[1].data["status"] == 200
        assert records[1].data["duration"].endswith("ms")

    def test_sync_log_redacts_the_token(self, request_mock, caplog):
        request_mock.return_value = sync_response({})
        api = SyncFPA("super-secret-token", AddressType.ADMINISTRATIVE)

        with caplog.at_level(logging.DEBUG, logger=SYNC_LOGGER):
            api.get_regions()

        assert "super-secret-token" not in caplog.text
        assert logged_records(caplog)[0].data["headers"]["master-token"] == "[REDACTED]"

    def test_sync_logs_the_post_body(self, request_mock, caplog):
        request_mock.return_value = sync_response({})
        api = SyncFPA("token-value", AddressType.ADMINISTRATIVE)

        with caplog.at_level(logging.DEBUG, logger=SYNC_LOGGER):
            api.get_address_items(address_level=7)

        assert '"address_level": 7' in logged_records(caplog)[0].data["body"]

    def test_sync_logs_the_failing_response_before_raising(
        self, request_mock, caplog
    ):
        """The error body is the most useful part of a failure, so it is logged."""
        response = sync_response({"error": "unauthorized"}, status_code=401)
        response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        request_mock.return_value = response
        api = SyncFPA("token-value", AddressType.ADMINISTRATIVE)

        with (
            caplog.at_level(logging.DEBUG, logger=SYNC_LOGGER),
            pytest.raises(HTTPError),
        ):
            api.get_regions()

        records = logged_records(caplog)
        assert [r.getMessage() for r in records] == ["http request", "http response"]
        assert records[1].data["status"] == 401
        assert "unauthorized" in records[1].data["body"]

    async def test_async_logs_the_request_and_the_response(self, caplog):
        api = AsyncFPA("token-value", AddressType.ADMINISTRATIVE)
        client = AsyncMock()
        client.get = AsyncMock(return_value=async_response({"addresses": []}))
        api._client = client

        with caplog.at_level(logging.DEBUG, logger=ASYNC_LOGGER):
            await api.get_regions()

        records = logged_records(caplog)
        assert [r.getMessage() for r in records] == ["http request", "http response"]
        assert records[0].data["method"] == "GET"
        assert records[0].data["url"] == GET_REGIONS
        assert records[1].data["status"] == 200

    async def test_async_log_redacts_the_token(self, caplog):
        api = AsyncFPA("super-secret-token", AddressType.ADMINISTRATIVE)
        client = AsyncMock()
        client.get = AsyncMock(return_value=async_response({}))
        api._client = client

        with caplog.at_level(logging.DEBUG, logger=ASYNC_LOGGER):
            await api.get_regions()

        assert "super-secret-token" not in caplog.text

    def test_enable_logging_does_not_grow_the_sync_handler_list(self):
        logger = logging.getLogger(SYNC_LOGGER)
        SyncFPA("token-value", AddressType.ADMINISTRATIVE, enable_logging=True)
        count = len(logger.handlers)

        for _ in range(3):
            SyncFPA("token-value", AddressType.ADMINISTRATIVE, enable_logging=True)

        assert len(logger.handlers) == count
        assert any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers)

    def test_enable_logging_does_not_grow_the_async_handler_list(self):
        logger = logging.getLogger(ASYNC_LOGGER)
        AsyncFPA("token-value", AddressType.ADMINISTRATIVE, enable_logging=True)
        count = len(logger.handlers)

        for _ in range(3):
            AsyncFPA("token-value", AddressType.ADMINISTRATIVE, enable_logging=True)

        assert len(logger.handlers) == count
        assert any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers)
