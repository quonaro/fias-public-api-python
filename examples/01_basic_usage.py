"""
Basic usage example for FIAS Public API.

This example demonstrates basic operations:
- Getting a token
- Creating a client
- Searching for addresses
- Getting address details
"""

from fias_public_api import AddressType, SyncFPA, get_token_sync


def main():
    # Step 1: Get authentication token
    print("🔑 Getting authentication token...")
    token = get_token_sync()
    print(f"✅ Token received: {token[:20]}...")

    # Step 2: Create API client
    print("\n📦 Creating API client...")
    api = SyncFPA(token, address_type=AddressType.MUNICIPALITY)
    print("✅ Client created")

    # Step 3: Search for addresses
    print("\n🔍 Searching for addresses...")
    search_query = "Москва, Красная площадь"
    results = api.search(search_query)
    print(f"✅ Found {len(results)} results")

    # Step 4: Display search results
    if results:
        print("\n📋 Search results:")
        for i, result in enumerate(results[:5], 1):  # Show first 5 results
            print(f"  {i}. {result.get('full_name', 'N/A')}")
            print(f"     ID: {result.get('object_id', 'N/A')}")

    # Step 5: Get details for first result
    if results:
        print("\n📄 Getting details for first result...")
        first_result = results[0]
        object_id = first_result.get("object_id")

        if object_id:
            details = api.details_by_id(object_id)
            print("✅ Details retrieved")
            if "addresses" in details and details["addresses"]:
                address = details["addresses"][0]
                print(f"   Full name: {address.get('full_name', 'N/A')}")
                print(f"   Path: {address.get('path', 'N/A')}")


if __name__ == "__main__":
    main()
