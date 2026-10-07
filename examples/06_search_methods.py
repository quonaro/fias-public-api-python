"""
Example demonstrating Search methods.

This example shows different search operations:
- SearchAddressItems - search by text string
- GetAddressHint - get address hints (GET and POST)
- SearchAddressItem - get single address item
"""

from fias_public_api import AddressType, SyncFPA, get_token_sync


def main():
    # Get token and create client
    token = get_token_sync()
    api = SyncFPA(token, address_type=AddressType.MUNICIPALITY)

    print("🔍 Search Methods Examples\n")

    # Example 1: SearchAddressItems
    print("1️⃣ Using search_address_items...")
    try:
        results = api.search_address_items("Москва, Красная площадь")
        addresses = results.get("addresses", [])
        print(f"✅ Found {len(addresses)} addresses")

        if addresses:
            print("\n📋 Results:")
            for i, addr in enumerate(addresses[:3], 1):
                print(f"   {i}. {addr.get('full_name', 'N/A')}")
                print(f"      ID: {addr.get('object_id', 'N/A')}")
                print(f"      Path: {addr.get('path', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 2: GetAddressHint (GET method)
    print("\n2️⃣ Using get_address_hint (GET method)...")
    try:
        results = api.get_address_hint(search_string="Москва")
        hints = results.get("hints", [])
        print(f"✅ Found {len(hints)} hints")

        if hints:
            print("\n📋 First 3 hints:")
            for i, hint in enumerate(hints[:3], 1):
                print(f"   {i}. {hint.get('full_name', 'N/A')}")
                print(f"      Path: {hint.get('path', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 3: GetAddressHint (POST method)
    print("\n3️⃣ Using get_address_hint (POST method)...")
    try:
        results = api.get_address_hint(up_to_level=5, search_non_active=False)
        hints = results.get("hints", [])
        print("✅ Retrieved hints (POST method)")
        print(f"   Found {len(hints)} hints")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 4: SearchAddressItem (single result)
    print("\n4️⃣ Using search_address_item (single result)...")
    try:
        result = api.search_address_item("Москва, Красная площадь, 1")

        if "object_id" in result:
            print("✅ Found address item")
            print(f"   Object ID: {result.get('object_id', 'N/A')}")
            print(f"   Full name: {result.get('full_name', 'N/A')}")
            print(f"   Path: {result.get('path', 'N/A')}")
        else:
            print("⚠️ No address item found")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 5: Using search wrapper method
    print("\n5️⃣ Using search wrapper method...")
    try:
        results = api.search("Санкт-Петербург")
        print(f"✅ Found {len(results)} results")

        if results:
            print("\n📋 First 3 results:")
            for i, result in enumerate(results[:3], 1):
                print(f"   {i}. {result.get('full_name', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
