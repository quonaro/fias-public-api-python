"""
Example demonstrating AddressType usage.

This example shows how to use different address types:
- Administrative division (ADMINISTRATIVE)
- Municipal division (MUNICIPALITY)
"""

from fias_public_api import AddressType, SyncFPA, get_token_sync


def main():
    # Get token
    token = get_token_sync()

    # Create client with default address type (MUNICIPALITY)
    print("🏛️ Using default address type (MUNICIPALITY)...")
    api_municipality = SyncFPA(token, address_type=AddressType.MUNICIPALITY)

    # Create client with administrative address type
    print("🏛️ Using administrative address type...")
    api_administrative = SyncFPA(token, address_type=AddressType.ADMINISTRATIVE)

    # Search with different address types
    search_query = "Москва"

    print(f"\n🔍 Searching for '{search_query}' with MUNICIPALITY type...")
    results_municipality = api_municipality.search_address_items(search_query)
    print(f"✅ Found {len(results_municipality.get('addresses', []))} results")

    print(f"\n🔍 Searching for '{search_query}' with ADMINISTRATIVE type...")
    results_administrative = api_administrative.search_address_items(search_query)
    print(f"✅ Found {len(results_administrative.get('addresses', []))} results")

    # Override address type for specific request
    print("\n🔍 Searching with overridden address type...")
    results_override = api_municipality.search_address_items(
        search_query,
        address_type=AddressType.ADMINISTRATIVE
    )
    print(f"✅ Found {len(results_override.get('addresses', []))} results")


if __name__ == "__main__":
    main()

