"""
Клиент для FIAS Public API (Python)

Библиотека для работы с публичным API ФИАС (Федеральная информационная адресная система).
Предоставляет простой доступ к функциям поиска адресов и получения детальной информации.

Пример:
    >>> from fias_public_api import SyncFPA, get_token_sync, AddressType
    >>> token = get_token_sync()
    >>> api = SyncFPA(token, AddressType.ADMINISTRATIVE)
    >>> results = api.search("Москва, Красная площадь")
    >>> details = api.details_by_id(12345)
"""

import json
import logging
import time
import warnings

import requests

from .constants import (
    DEFAULT_TIMEOUT,
    GET_ADDRESS_HINT,
    GET_ADDRESS_ITEM_BY_CADASTRAL_NUMBER,
    GET_ADDRESS_ITEM_BY_GUID,
    GET_ADDRESS_ITEM_BY_ID,
    GET_ADDRESS_ITEMS,
    GET_DETAILS,
    GET_FIAS_OBJECT_TYPES,
    GET_LOCATION_BY_IP,
    GET_REGIONS,
    HAS_DESCENDANTS,
    IS_DESCENDANT,
    SEARCH_ADDRESS_ITEM,
    SEARCH_ADDRESS_ITEMS,
    STANDARD_HEADERS,
    TOKEN_URL,
    AddressType,
    _safe_headers,
    _truncate_body,
    enable_console_logging,
    log_method_call,
)


def get_token_sync(url="https://fias.nalog.ru/", timeout=DEFAULT_TIMEOUT):
    """Получить токен аутентификации из сервиса ФИАС.

    Args:
        url (str): Базовый URL сервиса ФИАС
        timeout (float): Таймаут запроса в секундах

    Returns:
        str: Токен аутентификации

    Raises:
        ValueError: Если не удалось получить токен
        requests.RequestException: Если HTTP запрос завершился ошибкой
    """
    response = requests.get(TOKEN_URL, params={"url": url}, timeout=timeout)
    if response.status_code != 200:
        raise ValueError("Не удалось получить токен")
    payload = response.json()
    if "Token" not in payload:
        raise ValueError("Ответ сервиса не содержит токен")
    return payload["Token"]


# The client logger, configured once: a NullHandler keeps the library quiet by
# default, and every instance shares this logger instead of adding handlers of
# its own.
_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


class SyncFPA:
    """Основной класс клиента для работы с FIAS Public API.

    Этот класс предоставляет методы для поиска адресов и получения детальной информации
    об адресных объектах в системе ФИАС.

    Args:
        token (str): Токен аутентификации для доступа к API
        address_type (int | AddressType): Тип адреса (1 — административный, 2 — муниципальный).
            Используется по умолчанию для всех запросов. Может быть переопределён
            в конкретном методе через параметр address_type.
        enable_logging (bool): Включить вывод логов запросов в stdout
        log_level (int): Уровень логирования
        timeout (float): Таймаут каждого HTTP запроса в секундах
    """

    def __init__(
        self,
        token: str,
        address_type: int | AddressType,
        enable_logging: bool = False,
        log_level: int = logging.DEBUG,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.token = token
        self.address_type = int(address_type)
        self.timeout = timeout
        self._logger = _logger
        if enable_logging:
            enable_console_logging(self._logger, log_level)

    def _get_address_type(self, address_type: int | AddressType | None) -> int:
        """Получить тип адреса, используя значение по умолчанию из конструктора если не указано."""
        if address_type is None:
            return self.address_type
        return int(address_type)

    def _log_request(self, method, url, headers, params, body):
        if self._logger.isEnabledFor(logging.DEBUG):
            record = self._logger.makeRecord(
                self._logger.name,
                logging.DEBUG,
                "",
                0,
                "http request",
                (),
                None,
            )
            record.data = {
                "method": method,
                "url": url,
                "headers": _safe_headers(headers),
                "params": params,
                "body": _truncate_body(body),
            }
            self._logger.handle(record)

    def _log_response(self, method, url, status, resp_headers, body, duration_ms):
        if self._logger.isEnabledFor(logging.DEBUG):
            record = self._logger.makeRecord(
                self._logger.name,
                logging.DEBUG,
                "",
                0,
                "http response",
                (),
                None,
            )
            record.data = {
                "method": method,
                "url": url,
                "status": status,
                "headers": dict(resp_headers) if resp_headers else {},
                "body": _truncate_body(body),
                "duration": f"{duration_ms:.3f}ms",
            }
            self._logger.handle(record)

    def _make_request(self, method, url, **kwargs):
        start = time.time()
        headers = kwargs.pop("headers", {})
        params = kwargs.pop("params", None)
        json_payload = kwargs.pop("json", None)
        body = json.dumps(json_payload) if json_payload else ""

        self._log_request(method.upper(), url, headers, params, body)

        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_payload,
            timeout=self.timeout,
            **kwargs,
        )

        duration_ms = (time.time() - start) * 1000
        self._log_response(
            method.upper(),
            url,
            response.status_code,
            response.headers,
            response.text,
            duration_ms,
        )
        # Log first, then raise: the error body is the most useful part of a
        # failing request and would otherwise be lost.
        response.raise_for_status()
        return response

    @log_method_call()
    def get_regions(self):
        """Получить список регионов.

        Returns:
            dict: Список регионов

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        response = self._make_request(
            "GET", GET_REGIONS, headers=STANDARD_HEADERS(self.token)
        )
        return response.json()

    @log_method_call()
    def get_address_items(
        self,
        path: str | None = None,
        address_level: int | None = None,
        address_levels: list[int] | None = None,
        name_part: str | None = None,
        address_type: int | AddressType | None = None,
        include_descendants: bool | None = None,
    ):
        """Получить список дочерних элементов, соответствующих заданным фильтрам.

        Args:
            path (str, optional): Путь к родительскому элементу
            address_level (int, optional): Уровень адреса
            address_levels (list[int], optional): Список уровней адресов
            name_part (str, optional): Часть названия для поиска
            address_type (int | AddressType, optional): Тип адреса. Если не указан,
                используется значение из конструктора.
            include_descendants (bool, optional): Включать ли дочерние элементы

        Returns:
            dict: Список адресных элементов

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        payload = {}
        if path is not None:
            payload["path"] = path
        if address_level is not None:
            payload["address_level"] = address_level
        if address_levels is not None:
            payload["address_levels"] = address_levels
        if name_part is not None:
            payload["name_part"] = name_part
        payload["address_type"] = self._get_address_type(address_type)
        if include_descendants is not None:
            payload["include_descendants"] = include_descendants

        response = self._make_request(
            "POST",
            GET_ADDRESS_ITEMS,
            json=payload,
            headers=STANDARD_HEADERS(self.token),
        )
        return response.json()

    @log_method_call()
    def get_details(self, object_id: int):
        """Получить дополнительную информацию для заданного адресного элемента.

        Args:
            object_id (int): Идентификатор адресного элемента

        Returns:
            dict: Дополнительная информация об адресном элементе

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        response = self._make_request(
            "GET",
            GET_DETAILS,
            params={"object_id": object_id},
            headers=STANDARD_HEADERS(self.token),
        )
        return response.json()

    @log_method_call()
    def is_descendant(
        self,
        ancestor: int,
        descendant: int,
        address_type: int | AddressType | None = None,
    ):
        """Проверка, является ли элемент ancestor родительским элементом в иерархии для элемента descendant.

        Args:
            ancestor (int): Идентификатор предполагаемого родительского элемента
            descendant (int): Идентификатор проверяемого дочернего элемента
            address_type (int | AddressType, optional): Тип адреса. Если не указан,
                используется значение из конструктора.

        Returns:
            dict: Результат проверки

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        params = {
            "ancestor": ancestor,
            "descendant": descendant,
            "address_type": self._get_address_type(address_type),
        }

        response = self._make_request(
            "GET", IS_DESCENDANT, params=params, headers=STANDARD_HEADERS(self.token)
        )
        return response.json()

    @log_method_call()
    def has_descendants(
        self,
        parent: int,
        up_to_level: int,
        address_type: int | AddressType | None = None,
    ):
        """Проверка наличия дочерних элементов у заданного элемента.

        Args:
            parent (int): Идентификатор родительского элемента
            up_to_level (int): Максимальный уровень иерархии для проверки
            address_type (int | AddressType, optional): Тип адреса. Если не указан,
                используется значение из конструктора.

        Returns:
            dict: Результат проверки

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        params = {
            "parent": parent,
            "up_to_level": up_to_level,
            "address_type": self._get_address_type(address_type),
        }

        response = self._make_request(
            "GET", HAS_DESCENDANTS, params=params, headers=STANDARD_HEADERS(self.token)
        )
        return response.json()

    @log_method_call()
    def details_by_id(
        self,
        object_id: int,
        address_type: int | AddressType | None = None,
    ):
        """Получение детальной информации об адресном элементе по его ID.

        Args:
            object_id (int): Идентификатор адресного элемента
            address_type (int | AddressType, optional): Тип адреса. Если не указан,
                используется значение из конструктора.

        Returns:
            dict: Адресный элемент с детальной информацией

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        params = {
            "object_id": object_id,
            "address_type": self._get_address_type(address_type),
        }

        response = self._make_request(
            "GET",
            GET_ADDRESS_ITEM_BY_ID,
            params=params,
            headers=STANDARD_HEADERS(self.token),
        )
        return response.json()

    @log_method_call()
    def details_by_guid(
        self,
        object_guid: str,
        address_type: int | AddressType | None = None,
    ):
        """Получение детальной информации об адресном элементе по его GUID.

        Args:
            object_guid (str): GUID адресного элемента
            address_type (int | AddressType, optional): Тип адреса. Если не указан,
                используется значение из конструктора.

        Returns:
            dict: Адресный элемент с детальной информацией

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        params = {
            "object_guid": object_guid,
            "address_type": self._get_address_type(address_type),
        }

        response = self._make_request(
            "GET",
            GET_ADDRESS_ITEM_BY_GUID,
            params=params,
            headers=STANDARD_HEADERS(self.token),
        )
        return response.json()

    @log_method_call()
    def get_address_item_by_cadastral_number(
        self, cadastral_number: str, address_type: int | AddressType | None = None
    ):
        """Получение адресного элемента по кадастровому номеру.

        Args:
            cadastral_number (str): Кадастровый номер
            address_type (int | AddressType, optional): Тип адреса. Если не указан,
                используется значение из конструктора.

        Returns:
            dict: Адресный элемент

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        params = {
            "cadastral_number": cadastral_number,
            "address_type": self._get_address_type(address_type),
        }

        response = self._make_request(
            "GET",
            GET_ADDRESS_ITEM_BY_CADASTRAL_NUMBER,
            params=params,
            headers=STANDARD_HEADERS(self.token),
        )
        return response.json()

    @log_method_call()
    def get_fias_object_types(self):
        """Получение типов объектов ФИАС.

        Returns:
            dict: Список типов объектов ФИАС

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        response = self._make_request(
            "GET", GET_FIAS_OBJECT_TYPES, headers=STANDARD_HEADERS(self.token)
        )
        return response.json()

    @log_method_call()
    def search_address_items(
        self, search_string: str, address_type: int | AddressType | None = None
    ):
        """Получение адресных элементов, соответствующих заданной произвольной строке адреса.

        Args:
            search_string (str): Адрес строкой
            address_type (int | AddressType, optional): Вид представления адреса. Если не указан,
                используется значение из конструктора.

        Returns:
            dict: Список адресных элементов

        Raises:
            ValueError: Если search_string пустая строка
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        if not search_string.strip():
            raise ValueError("search_string cannot be empty")

        params = {
            "search_string": search_string,
            "address_type": self._get_address_type(address_type),
        }

        response = self._make_request(
            "GET",
            SEARCH_ADDRESS_ITEMS,
            params=params,
            headers=STANDARD_HEADERS(self.token),
        )
        return response.json()

    @log_method_call()
    def get_address_hint(
        self,
        search_string: str | None = None,
        address_type: int | AddressType | None = None,
        up_to_level: int | None = None,
        locations_boost: int | None = None,
        search_non_active: bool = False,
    ):
        """Сервис для организации стандартизированного ввода и поиска адреса (унифицированная адресная строка).

        Args:
            search_string (str, optional): Адрес строкой
            address_type (int | AddressType, optional): Вид представления адреса. Если не указан,
                используется значение из конструктора.
            up_to_level (int, optional): Максимальный уровень поиска
            locations_boost (int, optional): Приоритет локаций
            search_non_active (bool): Искать неактивные адреса

        Returns:
            dict: Список подсказок адресов

        Raises:
            ValueError: Если search_string пустая строка
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        if search_string is not None:
            # Validate search_string is not empty
            if not search_string.strip():
                raise ValueError("search_string cannot be empty")
            # GET request
            params = {
                "search_string": search_string,
                "address_type": self._get_address_type(address_type),
            }

            response = self._make_request(
                "GET",
                GET_ADDRESS_HINT,
                params=params,
                headers=STANDARD_HEADERS(self.token),
            )
        else:
            # POST request
            payload = {"searchNonActive": search_non_active}
            payload["addressType"] = self._get_address_type(address_type)
            if up_to_level is not None:
                payload["upToLevel"] = up_to_level
            if locations_boost is not None:
                payload["locationsBoost"] = locations_boost

            response = self._make_request(
                "POST",
                GET_ADDRESS_HINT,
                json=payload,
                headers=STANDARD_HEADERS(self.token),
            )
        return response.json()

    @log_method_call()
    def search_address_item(
        self, search_string: str, address_type: int | AddressType | None = None
    ):
        """Получение адресного элемента, соответствующего заданной произвольной строке адреса.

        Args:
            search_string (str): Адрес строкой
            address_type (int | AddressType, optional): Вид представления адреса. Если не указан,
                используется значение из конструктора.

        Returns:
            dict: Адресный элемент

        Raises:
            ValueError: Если search_string пустая строка
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        if not search_string.strip():
            raise ValueError("search_string cannot be empty")

        params = {
            "search_string": search_string,
            "address_type": self._get_address_type(address_type),
        }

        response = self._make_request(
            "GET",
            SEARCH_ADDRESS_ITEM,
            params=params,
            headers=STANDARD_HEADERS(self.token),
        )
        return response.json()

    @log_method_call()
    def get_location_by_ip(
        self, ip: str, address_type: int | AddressType | None = None
    ):
        """Получение населённого пункта по IP адресу.

        Args:
            ip (str): IP адрес
            address_type (int | AddressType, optional): Тип представления возвращаемых адресных объектов.
                Если не указан, используется значение из конструктора.

        Returns:
            dict: Адресные объекты

        Raises:
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        params = {
            "ip": ip,
            "address_type": self._get_address_type(address_type),
        }

        response = self._make_request(
            "GET",
            GET_LOCATION_BY_IP,
            params=params,
            headers=STANDARD_HEADERS(self.token),
        )
        return response.json()

    @log_method_call()
    def details(self, object_id: int, address_type: int | AddressType | None = None):
        """Устаревший метод. Используйте details_by_id вместо этого."""
        # stacklevel=3: this method is wrapped by log_method_call, so the caller
        # sits two frames above the wrapper.
        warnings.warn(
            "details() устарел, используйте details_by_id вместо этого",
            DeprecationWarning,
            stacklevel=3,
        )
        return self.details_by_id(object_id, address_type)

    @log_method_call()
    def search(
        self,
        search_string: str,
        address_type: int | AddressType | None = None,
    ):
        """Поиск адресов по текстовой строке (обертка над get_address_hint).

        Args:
            search_string (str): Текст для поиска (адрес, улица и т.д.)
            address_type (int | AddressType, optional): Тип адреса. Если не указан,
                используется значение из конструктора.

        Returns:
            list: Список подсказок адресов, соответствующих поисковому запросу

        Raises:
            ValueError: Если search_string пустая строка
            requests.HTTPError: Если HTTP запрос завершился ошибкой
        """
        result = self.get_address_hint(
            search_string=search_string, address_type=address_type
        )
        return result.get("hints", [])
