"""Endpoint table shared by the sync and async suites.

Both clients are supposed to expose the same endpoints with the same HTTP verb
and URL. Driving both suites from one table means a method that drifts — or
that exists in only one client — fails a test instead of going unnoticed.
"""

from fias_public_api.constants import (
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
)

# (case name, client method, call, HTTP verb, URL)
CASES = [
    ("get_regions", "get_regions", lambda api: api.get_regions(), "get", GET_REGIONS),
    (
        "get_address_items",
        "get_address_items",
        lambda api: api.get_address_items(address_level=1),
        "post",
        GET_ADDRESS_ITEMS,
    ),
    (
        "get_details",
        "get_details",
        lambda api: api.get_details(object_id=1),
        "get",
        GET_DETAILS,
    ),
    (
        "is_descendant",
        "is_descendant",
        lambda api: api.is_descendant(ancestor=1, descendant=2),
        "get",
        IS_DESCENDANT,
    ),
    (
        "has_descendants",
        "has_descendants",
        lambda api: api.has_descendants(parent=1, up_to_level=5),
        "get",
        HAS_DESCENDANTS,
    ),
    (
        "details_by_id",
        "details_by_id",
        lambda api: api.details_by_id(object_id=1),
        "get",
        GET_ADDRESS_ITEM_BY_ID,
    ),
    (
        "details_by_guid",
        "details_by_guid",
        lambda api: api.details_by_guid(object_guid="guid"),
        "get",
        GET_ADDRESS_ITEM_BY_GUID,
    ),
    (
        "get_address_item_by_cadastral_number",
        "get_address_item_by_cadastral_number",
        lambda api: api.get_address_item_by_cadastral_number(cadastral_number="1:2"),
        "get",
        GET_ADDRESS_ITEM_BY_CADASTRAL_NUMBER,
    ),
    (
        "get_fias_object_types",
        "get_fias_object_types",
        lambda api: api.get_fias_object_types(),
        "get",
        GET_FIAS_OBJECT_TYPES,
    ),
    (
        "search_address_items",
        "search_address_items",
        lambda api: api.search_address_items(search_string="Москва"),
        "get",
        SEARCH_ADDRESS_ITEMS,
    ),
    (
        "get_address_hint via GET",
        "get_address_hint",
        lambda api: api.get_address_hint(search_string="Москва"),
        "get",
        GET_ADDRESS_HINT,
    ),
    (
        "get_address_hint via POST",
        "get_address_hint",
        lambda api: api.get_address_hint(up_to_level=5),
        "post",
        GET_ADDRESS_HINT,
    ),
    (
        "search_address_item",
        "search_address_item",
        lambda api: api.search_address_item(search_string="Москва"),
        "get",
        SEARCH_ADDRESS_ITEM,
    ),
    (
        "get_location_by_ip",
        "get_location_by_ip",
        lambda api: api.get_location_by_ip(ip="8.8.8.8"),
        "get",
        GET_LOCATION_BY_IP,
    ),
]

IDS = [case for case, *_ in CASES]
PARAMS = [(call, verb, url) for _, _, call, verb, url in CASES]
METHODS = {method for _, method, *_ in CASES}

# Covered by their own tests rather than the table: `details` is a deprecated
# wrapper, `search` wraps `get_address_hint` and returns a list.
NOT_IN_TABLE = {"details", "search"}
