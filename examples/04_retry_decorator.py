"""
Example demonstrating retry_on_error decorator usage.

This example shows how to use the retry decorator to handle
connection errors and 500 errors that often occur on first request.
"""

from requests.exceptions import ConnectionError, HTTPError

from fias_public_api import AddressType, SyncFPA, get_token_sync, retry_on_error


# Apply retry decorator to a function that uses the API
@retry_on_error(
    max_retries=5, delay=0.5, backoff=2.0, exceptions=(ConnectionError, HTTPError)
)
def search_with_retry(api: SyncFPA, search_string: str):
    """Search for addresses with automatic retry on errors."""
    return api.search_address_items(search_string)


# Apply retry decorator to get_token function
@retry_on_error(max_retries=3, delay=1.0)
def get_token_with_retry():
    """Get token with automatic retry."""
    return get_token_sync()


def main():
    print("🔄 Example: Using retry_on_error decorator\n")

    # Example 1: Get token with retry
    print("1️⃣ Getting token with retry decorator...")
    try:
        token = get_token_with_retry()
        print(f"✅ Token received: {token[:20]}...")
    except Exception as e:
        print(f"❌ Failed after retries: {e}")
        return

    # Example 2: Create API client
    print("\n2️⃣ Creating API client...")
    api = SyncFPA(token, address_type=AddressType.MUNICIPALITY)

    # Example 3: Search with retry
    print("\n3️⃣ Searching with retry decorator...")
    try:
        results = search_with_retry(api, "Москва")
        addresses = results.get("addresses", [])
        print(f"✅ Found {len(addresses)} addresses")

        if addresses:
            print("\n📋 First result:")
            first = addresses[0]
            print(f"   Full name: {first.get('full_name', 'N/A')}")
            print(f"   Object ID: {first.get('object_id', 'N/A')}")
    except Exception as e:
        print(f"❌ Failed after retries: {e}")

    # Example 4: Custom retry for specific method
    print("\n4️⃣ Using retry with custom exceptions...")

    @retry_on_error(max_retries=3, delay=0.5, exceptions=(ConnectionError,))
    def get_regions_with_retry(api: SyncFPA):
        return api.get_regions()

    try:
        regions = get_regions_with_retry(api)
        print("✅ Retrieved regions")
        if "addresses" in regions:
            print(f"   Found {len(regions['addresses'])} regions")
    except Exception as e:
        print(f"❌ Failed: {e}")


if __name__ == "__main__":
    main()
